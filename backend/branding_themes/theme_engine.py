"""
Branding & Themes - Engine
"""

import logging
from typing import Optional, List
from .models import BrandTheme

logger = logging.getLogger(__name__)

class ThemeEngine:
    """Custom branding theme engine"""
    
    def __init__(self, db=None):
        self.db = db
        self.active_theme: Optional[BrandTheme] = None
        self.themes_cache = {}
    
    async def create_theme(self, theme: BrandTheme) -> BrandTheme:
        """Create a custom theme"""
        self.themes_cache[theme.id] = theme
        
        if self.db:
            await self.db.brand_themes.insert_one(theme.model_dump())
        
        logger.info(f"Theme created: {theme.name}")
        return theme
    
    async def activate_theme(self, theme_id: str) -> bool:
        """Activate a theme"""
        if theme_id in self.themes_cache:
            # Deactivate all
            for theme in self.themes_cache.values():
                theme.is_active = False
            
            # Activate selected
            self.themes_cache[theme_id].is_active = True
            self.active_theme = self.themes_cache[theme_id]
            
            logger.info(f"Theme activated: {self.active_theme.name}")
            return True
        
        return False
    
    def get_active_theme(self) -> Optional[BrandTheme]:
        """Get currently active theme"""
        return self.active_theme
    
    def generate_css(self, theme: BrandTheme) -> str:
        """Generate CSS from theme"""
        css = f"""
        :root {{
            --primary-color: {theme.primary_color};
            --secondary-color: {theme.secondary_color};
            --accent-color: {theme.accent_color};
            --background-color: {theme.background_color};
            --text-color: {theme.text_color};
            --font-family: {theme.font_family};
            --heading-font: {theme.heading_font};
        }}
        
        body {{
            background-color: var(--background-color);
            color: var(--text-color);
            font-family: var(--font-family);
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            font-family: var(--heading-font);
            color: var(--primary-color);
        }}
        
        .btn-primary {{
            background-color: var(--primary-color);
            color: var(--accent-color);
        }}
        
        .btn-secondary {{
            background-color: var(--secondary-color);
            color: var(--accent-color);
        }}
        
        {theme.custom_css or ''}
        """
        return css
