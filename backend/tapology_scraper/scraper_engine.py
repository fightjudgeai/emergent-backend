"""
Tapology Scraper Engine

Handles web scraping of MMA data from Tapology.com with rate limiting and error handling.
"""

import requests
from bs4 import BeautifulSoup
import time
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


class TapologyScraper:
    """Main scraper class for Tapology.com"""
    
    BASE_URL = "https://www.tapology.com"
    FIGHTCENTER_URL = f"{BASE_URL}/fightcenter"
    
    # Rate limiting: 1 request per 2 seconds to be respectful
    REQUEST_DELAY = 2.0
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; FightJudgeAI/1.0; +research)',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """Make HTTP request with rate limiting and error handling"""
        try:
            self._rate_limit()
            logger.info(f"Fetching: {url}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            return BeautifulSoup(response.content, 'lxml')
            
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
    
    def scrape_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape recent MMA events from Tapology FightCenter
        
        Args:
            limit: Maximum number of events to scrape
            
        Returns:
            List of event dictionaries
        """
        events = []
        
        try:
            # Fetch upcoming and recent results
            for schedule in ['', '?schedule=results']:
                url = f"{self.FIGHTCENTER_URL}{schedule}"
                soup = self._make_request(url)
                
                if not soup:
                    continue
                
                # Find event containers (this selector may need adjustment based on actual HTML)
                event_sections = soup.find_all('div', class_='fightcenterEvent') or soup.find_all('section', attrs={'data-name': True})
                
                # Fallback: look for event links
                if not event_sections:
                    event_links = soup.find_all('a', href=re.compile(r'/fightcenter/events/\d+'))
                    event_sections = [link.parent for link in event_links[:limit]]
                
                for section in event_sections[:limit]:
                    try:
                        event_data = self._parse_event_listing(section)
                        if event_data:
                            events.append(event_data)
                    except Exception as e:
                        logger.error(f"Error parsing event section: {e}")
                        continue
                
                if len(events) >= limit:
                    break
            
            logger.info(f"Scraped {len(events)} events from Tapology")
            return events[:limit]
            
        except Exception as e:
            logger.error(f"Error scraping recent events: {e}")
            return events
    
    def _parse_event_listing(self, section) -> Optional[Dict[str, Any]]:
        """Parse an event listing section"""
        try:
            # Extract event link
            event_link = section.find('a', href=re.compile(r'/fightcenter/events/\d+'))
            if not event_link:
                return None
            
            event_url = event_link.get('href')
            event_id = re.search(r'/events/(\d+)', event_url)
            event_id = event_id.group(1) if event_id else str(uuid.uuid4())
            
            # Extract event name
            event_name = event_link.get_text(strip=True)
            
            # Extract date info
            date_text = section.find(string=re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'))
            event_date = self._parse_date(date_text) if date_text else None
            
            # Extract promotion
            promotion_img = section.find('img', alt=True)
            promotion = promotion_img.get('alt', 'Unknown') if promotion_img else 'Unknown'
            
            # Extract location
            location_text = section.find(string=re.compile(r'[A-Z]{2}$'))  # Country code
            location = location_text.strip() if location_text else 'Unknown'
            
            return {
                'tapology_id': event_id,
                'event_name': event_name,
                'event_date': event_date,
                'promotion': promotion,
                'location': location,
                'tapology_url': f"{self.BASE_URL}{event_url}",
                'scraped_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing event listing: {e}")
            return None
    
    def scrape_event_details(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Scrape detailed information about a specific event
        
        Args:
            event_id: Tapology event ID
            
        Returns:
            Event details including fight card
        """
        url = f"{self.FIGHTCENTER_URL}/events/{event_id}"
        soup = self._make_request(url)
        
        if not soup:
            return None
        
        try:
            event_data = {
                'tapology_id': event_id,
                'fights': [],
                'scraped_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Extract event title
            title = soup.find('h1') or soup.find('h2', class_='eventPageTitle')
            if title:
                event_data['event_name'] = title.get_text(strip=True)
            
            # Extract fights from fight card
            fight_rows = soup.find_all('li', class_='fightCard') or soup.find_all('div', class_='bout')
            
            for fight_row in fight_rows:
                fight_data = self._parse_fight_row(fight_row)
                if fight_data:
                    event_data['fights'].append(fight_data)
            
            logger.info(f"Scraped event {event_id} with {len(event_data['fights'])} fights")
            return event_data
            
        except Exception as e:
            logger.error(f"Error scraping event details for {event_id}: {e}")
            return None
    
    def _parse_fight_row(self, fight_row) -> Optional[Dict[str, Any]]:
        """Parse a fight row from an event page"""
        try:
            # Extract fighter links
            fighter_links = fight_row.find_all('a', href=re.compile(r'/fightcenter/fighters/\d+'))
            
            if len(fighter_links) < 2:
                return None
            
            fighter1 = self._extract_fighter_info(fighter_links[0])
            fighter2 = self._extract_fighter_info(fighter_links[1])
            
            # Extract weight class
            weight_text = fight_row.find(string=re.compile(r'\d{3}'))
            weight_class = weight_text.strip() if weight_text else None
            
            # Extract bout link
            bout_link = fight_row.find('a', href=re.compile(r'/fightcenter/bouts/\d+'))
            bout_id = None
            if bout_link:
                bout_match = re.search(r'/bouts/(\d+)', bout_link.get('href'))
                bout_id = bout_match.group(1) if bout_match else None
            
            return {
                'bout_id': bout_id,
                'fighter1': fighter1,
                'fighter2': fighter2,
                'weight_class': weight_class
            }
            
        except Exception as e:
            logger.error(f"Error parsing fight row: {e}")
            return None
    
    def _extract_fighter_info(self, fighter_link) -> Dict[str, str]:
        """Extract fighter information from a link"""
        fighter_url = fighter_link.get('href', '')
        fighter_name = fighter_link.get_text(strip=True)
        
        # Extract fighter ID
        fighter_id_match = re.search(r'/fighters/(\d+)', fighter_url)
        fighter_id = fighter_id_match.group(1) if fighter_id_match else None
        
        return {
            'tapology_id': fighter_id,
            'name': fighter_name,
            'tapology_url': f"{self.BASE_URL}{fighter_url}" if fighter_url else None
        }
    
    def scrape_fighter_profile(self, fighter_id: str) -> Optional[Dict[str, Any]]:
        """
        Scrape detailed fighter profile
        
        Args:
            fighter_id: Tapology fighter ID
            
        Returns:
            Fighter profile data
        """
        url = f"{self.FIGHTCENTER_URL}/fighters/{fighter_id}"
        soup = self._make_request(url)
        
        if not soup:
            return None
        
        try:
            profile = {
                'tapology_id': fighter_id,
                'tapology_url': url,
                'scraped_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Extract fighter name
            name_elem = soup.find('h1', class_='fighterUpcomingHeader') or soup.find('h1')
            if name_elem:
                profile['name'] = name_elem.get_text(strip=True)
            
            # Extract record (W-L-D format)
            record_elem = soup.find(string=re.compile(r'\d+-\d+-\d+'))
            if record_elem:
                profile['record'] = record_elem.strip()
            
            # Extract additional details
            details = soup.find_all('span', class_='fighterInfo')
            for detail in details:
                text = detail.get_text(strip=True)
                
                if 'Nickname' in text:
                    profile['nickname'] = text.replace('Nickname:', '').strip()
                elif 'Age' in text:
                    age_match = re.search(r'(\d+)', text)
                    if age_match:
                        profile['age'] = int(age_match.group(1))
                elif 'Weight Class' in text or 'Division' in text:
                    profile['weight_class'] = text.split(':')[-1].strip()
                elif 'Height' in text:
                    profile['height'] = text.split(':')[-1].strip()
                elif 'Reach' in text:
                    profile['reach'] = text.split(':')[-1].strip()
                elif 'Stance' in text:
                    profile['stance'] = text.split(':')[-1].strip().lower()
            
            logger.info(f"Scraped fighter profile: {profile.get('name', fighter_id)}")
            return profile
            
        except Exception as e:
            logger.error(f"Error scraping fighter profile {fighter_id}: {e}")
            return None
    
    def scrape_bout_details(self, bout_id: str) -> Optional[Dict[str, Any]]:
        """
        Scrape detailed bout information including result
        
        Args:
            bout_id: Tapology bout ID
            
        Returns:
            Bout details and result
        """
        url = f"{self.FIGHTCENTER_URL}/bouts/{bout_id}"
        soup = self._make_request(url)
        
        if not soup:
            return None
        
        try:
            bout_data = {
                'tapology_id': bout_id,
                'tapology_url': url,
                'scraped_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Extract fighters
            fighter_links = soup.find_all('a', href=re.compile(r'/fightcenter/fighters/\d+'))[:2]
            if len(fighter_links) >= 2:
                bout_data['fighter1'] = self._extract_fighter_info(fighter_links[0])
                bout_data['fighter2'] = self._extract_fighter_info(fighter_links[1])
            
            # Extract result
            result_elem = soup.find('div', class_='boutResult') or soup.find(string=re.compile(r'(def\.|defeated)'))
            if result_elem:
                result_text = result_elem.get_text(strip=True) if hasattr(result_elem, 'get_text') else result_elem
                bout_data['result'] = self._parse_result(result_text)
            
            # Extract method and round
            method_elem = soup.find(string=re.compile(r'(KO/TKO|Submission|Decision|DQ)'))
            if method_elem:
                bout_data['method'] = method_elem.strip()
            
            round_elem = soup.find(string=re.compile(r'Round \d+'))
            if round_elem:
                round_match = re.search(r'Round (\d+)', round_elem)
                if round_match:
                    bout_data['round'] = int(round_match.group(1))
            
            logger.info(f"Scraped bout {bout_id}")
            return bout_data
            
        except Exception as e:
            logger.error(f"Error scraping bout {bout_id}: {e}")
            return None
    
    def _parse_result(self, result_text: str) -> Dict[str, str]:
        """Parse fight result text"""
        result = {
            'winner': None,
            'method': None,
            'round': None
        }
        
        # Extract winner
        if 'def.' in result_text or 'defeated' in result_text:
            parts = re.split(r'def\.|defeated', result_text)
            if len(parts) >= 2:
                result['winner'] = parts[0].strip()
        
        # Extract method
        methods = ['KO', 'TKO', 'Submission', 'Decision', 'DQ', 'NC']
        for method in methods:
            if method.lower() in result_text.lower():
                result['method'] = method
                break
        
        # Extract round
        round_match = re.search(r'R(\d+)', result_text)
        if round_match:
            result['round'] = int(round_match.group(1))
        
        return result
    
    def _parse_date(self, date_text: str) -> Optional[str]:
        """Parse date string to ISO format"""
        try:
            # Handle various date formats from Tapology
            # Example: "Nov 26, 2025" or "Friday, November 28"
            date_text = date_text.strip()
            
            # Try common formats
            for fmt in ['%b %d, %Y', '%B %d, %Y', '%b %d', '%B %d']:
                try:
                    dt = datetime.strptime(date_text, fmt)
                    # If no year, assume current year
                    if fmt in ['%b %d', '%B %d']:
                        dt = dt.replace(year=datetime.now().year)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing date '{date_text}': {e}")
            return None
    
    def search_fighter(self, fighter_name: str) -> Optional[str]:
        """
        Search for a fighter by name and return their Tapology ID
        
        Args:
            fighter_name: Name to search for
            
        Returns:
            Tapology fighter ID if found
        """
        try:
            # Use Tapology search (this is a simplified version)
            search_url = f"{self.BASE_URL}/search?term={fighter_name.replace(' ', '+')}"
            soup = self._make_request(search_url)
            
            if not soup:
                return None
            
            # Find first fighter result
            fighter_link = soup.find('a', href=re.compile(r'/fightcenter/fighters/\d+'))
            if fighter_link:
                match = re.search(r'/fighters/(\d+)', fighter_link.get('href'))
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching for fighter '{fighter_name}': {e}")
            return None
