import React, { useState, useEffect } from 'react';
import { Filter, ChevronDown } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || import.meta.env.VITE_BACKEND_URL;

const SportOrgSelector = ({ onFilterChange, showOrganization = true }) => {
  const [sportTypes, setSportTypes] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [selectedSport, setSelectedSport] = useState('');
  const [selectedOrg, setSelectedOrg] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSportTypes();
  }, []);

  useEffect(() => {
    if (selectedSport) {
      loadOrganizations(selectedSport);
    } else {
      setOrganizations([]);
      setSelectedOrg('');
    }
  }, [selectedSport]);

  useEffect(() => {
    // Notify parent of filter changes
    if (onFilterChange) {
      onFilterChange({
        sport_type: selectedSport || null,
        organization_id: selectedOrg || null
      });
    }
  }, [selectedSport, selectedOrg, onFilterChange]);

  const loadSportTypes = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/sports/types`);
      const data = await response.json();
      
      if (data.sport_types) {
        setSportTypes(Object.entries(data.sport_types).map(([key, value]) => ({
          id: key,
          name: value.name,
          abbreviation: value.abbreviation
        })));
      }
    } catch (error) {
      console.error('Error loading sport types:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadOrganizations = async (sportType) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/sports/types/${sportType}/organizations`);
      const data = await response.json();
      
      if (data.organizations) {
        setOrganizations(data.organizations);
      }
    } catch (error) {
      console.error('Error loading organizations:', error);
      setOrganizations([]);
    }
  };

  const handleSportChange = (e) => {
    const sport = e.target.value;
    setSelectedSport(sport);
    setSelectedOrg(''); // Reset org when sport changes
  };

  const handleOrgChange = (e) => {
    setSelectedOrg(e.target.value);
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-400">
        <Filter className="w-4 h-4 animate-pulse" />
        <span className="text-sm">Loading...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2 text-gray-400">
        <Filter className="w-4 h-4" />
        <span className="text-sm font-medium">Filter:</span>
      </div>

      {/* Sport Type Selector */}
      <div className="relative">
        <select
          value={selectedSport}
          onChange={handleSportChange}
          className="appearance-none bg-gray-800 border border-gray-600 text-white px-4 py-2 pr-10 rounded-lg focus:outline-none focus:border-amber-500 hover:border-gray-500 transition-colors cursor-pointer"
        >
          <option value="">All Sports</option>
          {sportTypes.map((sport) => (
            <option key={sport.id} value={sport.id}>
              {sport.name}
            </option>
          ))}
        </select>
        <ChevronDown className="w-4 h-4 text-gray-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
      </div>

      {/* Organization Selector */}
      {showOrganization && selectedSport && (
        <div className="relative">
          <select
            value={selectedOrg}
            onChange={handleOrgChange}
            className="appearance-none bg-gray-800 border border-gray-600 text-white px-4 py-2 pr-10 rounded-lg focus:outline-none focus:border-amber-500 hover:border-gray-500 transition-colors cursor-pointer"
          >
            <option value="">All Organizations</option>
            {organizations.map((org) => (
              <option key={org.organization_id} value={org.organization_id}>
                {org.organization_id.toUpperCase()}
                {org.total_fights > 0 && ` (${org.total_fights} fights)`}
              </option>
            ))}
          </select>
          <ChevronDown className="w-4 h-4 text-gray-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      )}

      {/* Active Filters Badge */}
      {(selectedSport || selectedOrg) && (
        <button
          onClick={() => {
            setSelectedSport('');
            setSelectedOrg('');
          }}
          className="text-xs text-amber-400 hover:text-amber-300 underline"
        >
          Clear filters
        </button>
      )}
    </div>
  );
};

export default SportOrgSelector;
