import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import ICVSSPanel from '@/components/ICVSSPanel';
import RealtimeCVPanel from '@/components/RealtimeCVPanel';

const CVSystemsPage = () => {
  const { boutId } = useParams();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="bg-[#13151a] border border-[#2a2d35] rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                onClick={() => navigate(`/operator/${boutId}`)}
                variant="ghost"
                className="text-gray-400 hover:text-white"
              >
                <ArrowLeft className="h-5 w-5 mr-2" />
                Back to Operator Panel
              </Button>
              <div className="h-8 w-px bg-gray-700" />
              <div className="flex items-center gap-3">
                <Eye className="h-8 w-8 text-cyan-500" />
                <div>
                  <h1 className="text-3xl font-bold text-cyan-500">Computer Vision Systems</h1>
                  <p className="text-gray-400 text-sm mt-1">AI-Powered Fight Analysis & Scoring</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ICVSS - Intelligent Combat Vision Scoring System */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="mb-4">
          <h2 className="text-xl font-bold text-white">ICVSS - Intelligent Combat Vision Scoring</h2>
          <p className="text-gray-400 text-sm">Real-time computer vision scoring with 15+ microservices</p>
        </div>
        <ICVSSPanel boutId={boutId} currentRound={1} />
      </div>

      {/* Real-Time CV System - Professional Video Analysis */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="mb-4">
          <h2 className="text-xl font-bold text-white">Real-Time CV System</h2>
          <p className="text-gray-400 text-sm">Live video frame analysis with MediaPipe & YOLO</p>
        </div>
        <RealtimeCVPanel boutId={boutId} />
      </div>

      {/* Info Cards */}
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-cyan-900/20 to-blue-900/20 border border-cyan-500/30 rounded-lg p-6">
          <h3 className="text-lg font-bold text-cyan-400 mb-2">Frame Analysis</h3>
          <p className="text-gray-400 text-sm">
            Real-time processing of video frames using pre-trained models (MediaPipe, YOLO) for action detection and classification.
          </p>
        </div>

        <div className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/30 rounded-lg p-6">
          <h3 className="text-lg font-bold text-purple-400 mb-2">Event Detection</h3>
          <p className="text-gray-400 text-sm">
            Automatic detection of strikes, takedowns, submissions, and control positions with confidence scores.
          </p>
        </div>

        <div className="bg-gradient-to-br from-amber-900/20 to-orange-900/20 border border-amber-500/30 rounded-lg p-6">
          <h3 className="text-lg font-bold text-amber-400 mb-2">AI Scoring</h3>
          <p className="text-gray-400 text-sm">
            Automated scoring using multiple CV models with verification engine for quality assurance.
          </p>
        </div>
      </div>
    </div>
  );
};

export default CVSystemsPage;
