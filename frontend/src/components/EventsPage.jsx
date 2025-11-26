import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, TrendingUp, Users } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || import.meta.env.VITE_BACKEND_URL;

const EventsPage = () => {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/events`);
      
      if (!response.ok) {
        throw new Error('Failed to load events');
      }
      
      const data = await response.json();
      setEvents(data.events || []);
      setError(null);
    } catch (err) {
      console.error('Error loading events:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch {
      return 'Date TBA';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-amber-500 mx-auto mb-4"></div>
          <p className="text-gray-300 text-lg">Loading events...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center bg-red-900/20 border border-red-500 rounded-lg p-8">
          <p className="text-red-400 text-xl mb-4">Error loading events</p>
          <p className="text-gray-400 mb-6">{error}</p>
          <button
            onClick={loadEvents}
            className="px-6 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-amber-500 mb-2">Fight Events</h1>
          <p className="text-gray-400">Browse all combat sports events and statistics</p>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-gradient-to-br from-amber-900/30 to-amber-800/20 border border-amber-700/50 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm mb-1">Total Events</p>
                <p className="text-3xl font-bold text-amber-400">{events.length}</p>
              </div>
              <Calendar className="w-12 h-12 text-amber-500 opacity-50" />
            </div>
          </div>

          <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/20 border border-blue-700/50 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm mb-1">Total Fights</p>
                <p className="text-3xl font-bold text-blue-400">
                  {events.reduce((sum, e) => sum + (e.fight_count || 0), 0)}
                </p>
              </div>
              <Users className="w-12 h-12 text-blue-500 opacity-50" />
            </div>
          </div>

          <div className="bg-gradient-to-br from-red-900/30 to-red-800/20 border border-red-700/50 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm mb-1">Total Strikes</p>
                <p className="text-3xl font-bold text-red-400">
                  {events.reduce((sum, e) => sum + (e.total_strikes || 0), 0).toLocaleString()}
                </p>
              </div>
              <TrendingUp className="w-12 h-12 text-red-500 opacity-50" />
            </div>
          </div>
        </div>

        {/* Events List */}
        {events.length === 0 ? (
          <div className="text-center py-12 bg-gray-800/50 border border-gray-700 rounded-lg">
            <Calendar className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-lg">No events found</p>
            <p className="text-gray-500 text-sm mt-2">Events will appear here once fights are recorded</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {events.map((event, index) => (
              <div
                key={index}
                className="bg-gradient-to-r from-gray-800 to-gray-900 border border-gray-700 rounded-lg p-6 hover:border-amber-500 transition-all cursor-pointer group"
                onClick={() => {
                  // Navigate to first fight in this event (if available)
                  // For now, just show event details
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-2xl font-bold text-white mb-2 group-hover:text-amber-400 transition-colors">
                      {event.event_name || 'Unknown Event'}
                    </h3>
                    <div className="flex items-center gap-6 text-gray-400">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        <span>{formatDate(event.event_date)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        <span>{event.fight_count} {event.fight_count === 1 ? 'Fight' : 'Fights'}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <TrendingUp className="w-4 h-4" />
                        <span>{(event.total_strikes || 0).toLocaleString()} Strikes</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="text-3xl font-bold text-amber-500">
                      {Math.round((event.total_strikes || 0) / (event.fight_count || 1))}
                    </div>
                    <div className="text-xs text-gray-500 uppercase">Avg Strikes/Fight</div>
                  </div>
                </div>

                {/* Progress bar showing strike intensity */}
                <div className="mt-4">
                  <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-amber-600 to-red-600 rounded-full transition-all"
                      style={{
                        width: `${Math.min(100, ((event.total_strikes || 0) / (event.fight_count || 1)) / 5)}%`
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default EventsPage;
