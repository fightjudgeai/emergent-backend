import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, Pause, Edit2, Trash2, Merge, Check, X, 
  Clock, Users, AlertCircle, Video, Upload 
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || import.meta.env.VITE_BACKEND_URL;

const PostFightReviewPanel = ({ fightId, supervisorId }) => {
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedEvents, setSelectedEvents] = useState([]);
  const [editingEvent, setEditingEvent] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [currentTime, setCurrentTime] = useState(0);
  const videoRef = useRef(null);

  useEffect(() => {
    loadTimeline();
    loadVideo();
  }, [fightId]);

  const loadTimeline = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/review/timeline/${fightId}`);
      const data = await response.json();
      setTimeline(data);
    } catch (error) {
      console.error('Error loading timeline:', error);
      toast.error('Failed to load timeline');
    } finally {
      setLoading(false);
    }
  };

  const loadVideo = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/review/videos/${fightId}`);
      const data = await response.json();
      
      if (data.videos && data.videos.length > 0) {
        const video = data.videos[0];
        setVideoUrl(`${BACKEND_URL}/api/review/videos/stream/${video.video_id}`);
      }
    } catch (error) {
      console.error('Error loading video:', error);
    }
  };

  const handleEditEvent = async (eventId, updates, reason) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/review/events/${eventId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          updates,
          supervisor_id: supervisorId,
          reason
        })
      });

      if (!response.ok) throw new Error('Edit failed');

      toast.success('Event edited successfully');
      await loadTimeline();
      setEditingEvent(null);
    } catch (error) {
      console.error('Error editing event:', error);
      toast.error('Failed to edit event');
    }
  };

  const handleDeleteEvent = async (eventId, reason) => {
    if (!confirm('Are you sure you want to delete this event?')) return;

    try {
      const response = await fetch(
        `${BACKEND_URL}/api/review/events/${eventId}?supervisor_id=${supervisorId}&reason=${encodeURIComponent(reason)}`,
        { method: 'DELETE' }
      );

      if (!response.ok) throw new Error('Delete failed');

      toast.success('Event deleted successfully');
      await loadTimeline();
    } catch (error) {
      console.error('Error deleting event:', error);
      toast.error('Failed to delete event');
    }
  };

  const handleMergeEvents = async (mergedData) => {
    if (selectedEvents.length < 2) {
      toast.error('Select at least 2 events to merge');
      return;
    }

    try {
      const response = await fetch(`${BACKEND_URL}/api/review/events/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_ids: selectedEvents,
          supervisor_id: supervisorId,
          merged_data: mergedData
        })
      });

      if (!response.ok) throw new Error('Merge failed');

      toast.success(`Merged ${selectedEvents.length} events`);
      setSelectedEvents([]);
      await loadTimeline();
    } catch (error) {
      console.error('Error merging events:', error);
      toast.error('Failed to merge events');
    }
  };

  const handleApprove = async () => {
    if (!confirm('Approve all edits and trigger stat recalculation?')) return;

    try {
      const response = await fetch(
        `${BACKEND_URL}/api/review/fights/${fightId}/approve?supervisor_id=${supervisorId}`,
        { method: 'POST' }
      );

      if (!response.ok) throw new Error('Approval failed');

      const data = await response.json();
      toast.success('Fight approved! Stats recalculation triggered');
      console.log('Recalculation job:', data.job_id);
    } catch (error) {
      console.error('Error approving fight:', error);
      toast.error('Failed to approve fight');
    }
  };

  const handleVideoUpload = async (file) => {
    try {
      const formData = new FormData();
      formData.append('fight_id', fightId);
      formData.append('video', file);

      const response = await fetch(`${BACKEND_URL}/api/review/videos/upload`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error('Upload failed');

      toast.success('Video uploaded successfully');
      await loadVideo();
    } catch (error) {
      console.error('Error uploading video:', error);
      toast.error('Failed to upload video');
    }
  };

  const seekToEvent = (event) => {
    if (videoRef.current && event.timestamp) {
      // Calculate video time from event timestamp
      // This assumes video starts at fight start time
      const eventTime = new Date(event.timestamp).getTime();
      // Implement your logic to convert event timestamp to video time
      // videoRef.current.currentTime = calculatedTime;
    }
  };

  const toggleEventSelection = (eventId) => {
    setSelectedEvents(prev => 
      prev.includes(eventId) 
        ? prev.filter(id => id !== eventId)
        : [...prev, eventId]
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-amber-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-amber-500">Post-Fight Review</h1>
            <p className="text-gray-400">Fight ID: {fightId}</p>
          </div>
          
          <div className="flex items-center gap-3">
            {selectedEvents.length > 0 && (
              <button
                onClick={() => handleMergeEvents({})}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2"
              >
                <Merge className="w-4 h-4" />
                Merge {selectedEvents.length} Events
              </button>
            )}
            
            <button
              onClick={handleApprove}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg flex items-center gap-2"
            >
              <Check className="w-4 h-4" />
              Approve & Rerun Stats
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Video Player */}
          <div className="lg:col-span-2">
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <Video className="w-5 h-5 text-amber-500" />
                  Video Playback
                </h2>
                
                <label className="cursor-pointer px-3 py-1 bg-amber-600 hover:bg-amber-700 rounded text-sm flex items-center gap-2">
                  <Upload className="w-4 h-4" />
                  Upload Video
                  <input
                    type="file"
                    accept="video/*"
                    className="hidden"
                    onChange={(e) => e.target.files[0] && handleVideoUpload(e.target.files[0])}
                  />
                </label>
              </div>

              {videoUrl ? (
                <video
                  ref={videoRef}
                  src={videoUrl}
                  controls
                  className="w-full rounded bg-black"
                  onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
                />
              ) : (
                <div className="aspect-video bg-gray-700 rounded flex items-center justify-center">
                  <p className="text-gray-400">No video uploaded</p>
                </div>
              )}
            </div>

            {/* Timeline Stats */}
            <div className="mt-4 grid grid-cols-3 gap-4">
              <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <div className="text-sm text-gray-400">Total Events</div>
                <div className="text-3xl font-bold text-amber-500">
                  {timeline?.total_events || 0}
                </div>
              </div>
              
              <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <div className="text-sm text-gray-400">Rounds</div>
                <div className="text-3xl font-bold text-blue-500">
                  {timeline?.rounds ? Object.keys(timeline.rounds).length : 0}
                </div>
              </div>
              
              <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <div className="text-sm text-gray-400">Selected</div>
                <div className="text-3xl font-bold text-green-500">
                  {selectedEvents.length}
                </div>
              </div>
            </div>
          </div>

          {/* Event Timeline */}
          <div className="lg:col-span-1">
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 max-h-[600px] overflow-y-auto">
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Clock className="w-5 h-5 text-amber-500" />
                Event Timeline
              </h2>

              {timeline?.rounds && Object.entries(timeline.rounds).map(([roundNum, events]) => (
                <div key={roundNum} className="mb-6">
                  <div className="font-bold text-amber-500 mb-2 sticky top-0 bg-gray-800 py-1">
                    Round {roundNum}
                  </div>
                  
                  {events.map((event) => (
                    <div
                      key={event.id}
                      className={`mb-2 p-3 rounded border cursor-pointer transition-all ${
                        selectedEvents.includes(event.id)
                          ? 'border-blue-500 bg-blue-900/20'
                          : event.deleted
                          ? 'border-red-900 bg-red-900/10 opacity-50'
                          : 'border-gray-700 bg-gray-900/50 hover:border-gray-600'
                      }`}
                      onClick={() => !event.deleted && toggleEventSelection(event.id)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="font-semibold text-sm">
                            {event.event_type}
                            {event.deleted && (
                              <span className="ml-2 text-red-400 text-xs">(Deleted)</span>
                            )}
                          </div>
                          <div className="text-xs text-gray-400 mt-1">
                            Fighter: {event.fighter_id}
                          </div>
                          {event.target && (
                            <div className="text-xs text-gray-500">
                              Target: {event.target}
                            </div>
                          )}
                          {event.source && (
                            <div className="text-xs text-gray-500">
                              Source: <span className={
                                event.source === 'ai_cv' ? 'text-purple-400' :
                                event.source === 'judge_software' ? 'text-green-400' :
                                'text-blue-400'
                              }>{event.source}</span>
                            </div>
                          )}
                        </div>

                        {!event.deleted && (
                          <div className="flex gap-1">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setEditingEvent(event);
                              }}
                              className="p-1 hover:bg-gray-700 rounded"
                            >
                              <Edit2 className="w-4 h-4 text-blue-400" />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                const reason = prompt('Reason for deletion:');
                                if (reason) handleDeleteEvent(event.id, reason);
                              }}
                              className="p-1 hover:bg-gray-700 rounded"
                            >
                              <Trash2 className="w-4 h-4 text-red-400" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Edit Modal */}
      {editingEvent && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4 border border-gray-700">
            <h3 className="text-xl font-bold mb-4">Edit Event</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm mb-1 text-gray-400">Event Type</label>
                <input
                  type="text"
                  defaultValue={editingEvent.event_type}
                  id="edit-event-type"
                  className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600"
                />
              </div>

              <div>
                <label className="block text-sm mb-1 text-gray-400">Target</label>
                <input
                  type="text"
                  defaultValue={editingEvent.target || ''}
                  id="edit-target"
                  className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600"
                />
              </div>

              <div>
                <label className="block text-sm mb-1 text-gray-400">Reason for Edit</label>
                <textarea
                  id="edit-reason"
                  className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600"
                  rows="3"
                  placeholder="Explain why this edit is needed..."
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  const updates = {
                    event_type: document.getElementById('edit-event-type').value,
                    target: document.getElementById('edit-target').value
                  };
                  const reason = document.getElementById('edit-reason').value;
                  
                  if (!reason) {
                    toast.error('Reason is required');
                    return;
                  }
                  
                  handleEditEvent(editingEvent.id, updates, reason);
                }}
                className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 rounded"
              >
                Save Changes
              </button>
              <button
                onClick={() => setEditingEvent(null)}
                className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PostFightReviewPanel;
