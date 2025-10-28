import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  ThumbsUp,
  ThumbsDown,
  Edit3,
  Download,
  RefreshCw,
  XCircle,
  Eye,
  Video,
  FileText,
  Hash,
} from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import Card from '../components/Card';
import Button from '../components/Button';
import StatusBadge from '../components/StatusBadge';

interface Review {
  id: string;
  workflow_id: string;
  workflow_execution_id: string;
  reviewer_id: string | null;
  asset_type: string;
  asset_url: string | null;
  asset_metadata: {
    script?: string;
    duration?: number;
    platforms?: string[];
  } | null;
  status: 'pending' | 'in_review' | 'approved' | 'rejected';
  feedback: string | null;
  created_at: string;
  assigned_at: string | null;
  reviewed_at: string | null;
}

interface ContentItem {
  workflow_id: string;
  review_id: string; // Added for review API calls
  status: 'pending_review' | 'approved' | 'rejected' | 'published';
  created_at: string;
  video_url: string;
  script: string;
  captions: string;
  platforms: {
    name: 'tiktok' | 'youtube_shorts';
    title?: string;
    description?: string;
    hashtags?: string[];
    preview_url?: string;
  }[];
  metadata: {
    topic: string;
    audience: string;
    style: string;
    duration_seconds: number;
    cost_usd: number;
  };
  supervisor_decision?: {
    reasoning: string;
    confidence: number;
  };
}

export default function ContentReview() {
  const { workflowId } = useParams<{ workflowId: string }>();
  const navigate = useNavigate();

  const [content, setContent] = useState<ContentItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState<
    'tiktok' | 'youtube_shorts'
  >('tiktok');
  const [isEditing, setIsEditing] = useState(false);
  const [editedMetadata, setEditedMetadata] = useState<any>({});

  // Fetch actual workflow results from API
  useEffect(() => {
    const fetchContent = async () => {
      // Validate workflowId is a valid UUID format
      const isUUID =
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
          workflowId?.replace('wf-', '') || ''
        );

      if (!workflowId || workflowId === 'demo' || !isUUID) {
        console.warn(
          'Invalid workflow ID, redirecting to dashboard:',
          workflowId
        );
        navigate('/');
        return;
      }

      setLoading(true);
      try {
        // Import api client
        const { apiClient } = await import('../services/api');

        // Fetch real workflow results
        const data = await apiClient.getWorkflowResults(workflowId);

        // Map backend response to ContentItem format
        const contentData: ContentItem = {
          workflow_id: data.workflow_id,
          review_id: data.review_id || '', // Get review_id from backend
          status:
            data.status === 'completed' ? 'pending_review' : 'pending_review',
          created_at: new Date().toISOString(),
          video_url: data.video_url || '',
          script: data.script || '',
          captions: data.captions || '',
          platforms: [
            {
              name: 'tiktok',
              title: 'AI Content Creation',
              description: 'Generated content',
              hashtags: ['AI', 'ContentCreation'],
            },
          ],
          metadata: {
            topic: data.trend_topic || '',
            audience: 'General',
            style: 'Educational',
            duration_seconds: 6,
            cost_usd: data.total_cost_usd || 0,
          },
        };

        setContent(contentData);
      } catch (error) {
        console.error('Failed to load workflow results:', error);

        // Fallback to mock data if API fails
        const mockData: ContentItem = {
          workflow_id: workflowId || 'test-workflow-001',
          review_id: workflowId || 'test-review-001', // Use workflowId as fallback
          status: 'pending_review',
          created_at: new Date().toISOString(),
          video_url: 'https://example.com/video.mp4',
          script: `Hey everyone! Today we're diving into AI content creation tips for beginners.

First tip: Start with a clear hook in the first 3 seconds. This is crucial for viewer retention.

Second: Use platform-specific formatting. TikTok loves vertical 9:16 videos with trending sounds.

Third: Consistency is key. Post regularly to build your audience.

And finally: Use AI tools like this one to scale your content production!

Follow for more AI tips! #AIContentCreation #TikTokTips`,
          captions:
            'AI content creation tips for beginners 🚀 Follow for more! #AI #ContentCreation #TikTokTips',
          platforms: [
            {
              name: 'tiktok',
              title: 'AI Content Creation Tips for Beginners',
              description:
                'Master AI-powered content creation with these 4 essential tips! 🤖✨',
              hashtags: [
                'AIContentCreation',
                'TikTokTips',
                'ContentStrategy',
                'AITools',
                'BeginnerTips',
              ],
            },
            {
              name: 'youtube_shorts',
              title: '4 AI Content Tips Every Beginner Needs #Shorts',
              description: `Start your AI content creation journey with these pro tips! 🚀

In this Short, I share 4 essential strategies for beginners:
✅ Hook viewers in 3 seconds
✅ Use platform-specific formatting
✅ Post consistently
✅ Leverage AI tools for scale

🔔 Subscribe for more AI content tips!

#Shorts #AIContentCreation #YouTubeShorts #ContentStrategy #AITools`,
              hashtags: [
                'Shorts',
                'AIContentCreation',
                'YouTubeShorts',
                'ContentStrategy',
              ],
            },
          ],
          metadata: {
            topic: 'AI content creation tips',
            audience: 'beginners',
            style: 'educational',
            duration_seconds: 45,
            cost_usd: 0.42,
          },
          supervisor_decision: {
            reasoning:
              'Request aligns with educational content style and targets beginner audience. Similar to successful campaigns from last week.',
            confidence: 0.89,
          },
        };

        setContent(mockData);
        setEditedMetadata(
          mockData.platforms.find((p) => p.name === selectedPlatform)
        );
      } finally {
        setLoading(false);
      }
    };

    if (workflowId) {
      fetchContent();
    }
  }, [workflowId, selectedPlatform]);

  const handleApprove = async () => {
    if (!content?.review_id) {
      console.warn('Missing review_id in review payload');
      alert('Cannot approve: Review ID not found');
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8006/api/reviews/${content.review_id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            status: 'approved',
            feedback: 'Content looks great! Approved for publishing.',
          }),
        }
      );

      if (response.ok) {
        alert('Content approved! Publishing to platforms...');
        navigate('/dashboard');
      } else {
        const error = await response.json();
        alert(`Failed to approve: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error approving content:', error);
      alert('Failed to approve content. Please try again.');
    }
  };

  const handleReject = async () => {
    if (!content?.review_id) {
      console.warn('Missing review_id in review payload');
      alert('Cannot reject: Review ID not found');
      return;
    }

    const feedback = prompt('Please provide feedback for rejection:');
    if (!feedback) return;

    try {
      const response = await fetch(
        `http://localhost:8006/api/reviews/${content.review_id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            status: 'rejected',
            feedback,
          }),
        }
      );

      if (response.ok) {
        alert('Content rejected. Workflow terminated.');
        navigate('/dashboard');
      } else {
        const error = await response.json();
        alert(`Failed to reject: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error rejecting content:', error);
      alert('Failed to reject content. Please try again.');
    }
  };

  const handleRegenerate = async () => {
    // TODO: API call to regenerate content
    console.log('Regenerating content:', workflowId);
    alert('Regenerating content with different parameters...');
  };

  const handleSaveEdits = () => {
    // TODO: API call to update metadata
    console.log('Saving edits:', editedMetadata);
    if (content) {
      const updatedPlatforms = content.platforms.map((p) =>
        p.name === selectedPlatform ? { ...p, ...editedMetadata } : p
      );
      setContent({ ...content, platforms: updatedPlatforms });
    }
    setIsEditing(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
        >
          <RefreshCw className="w-8 h-8 text-primary-400" />
        </motion.div>
      </div>
    );
  }

  if (!content) {
    return (
      <Card className="text-center py-12">
        <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Content Not Found</h2>
        <p className="text-gray-400 mb-6">
          This workflow doesn't exist or has been deleted.
        </p>
        <Button onClick={() => navigate('/dashboard')}>
          Back to Dashboard
        </Button>
      </Card>
    );
  }

  const platformData = content.platforms.find(
    (p) => p.name === selectedPlatform
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col md:flex-row md:items-center md:justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold gradient-text mb-2">
            Content Review
          </h1>
          <p className="text-gray-400">
            Review and approve generated content before publishing
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={content.status} />
          <span className="text-sm text-gray-400">
            {new Date(content.created_at).toLocaleString()}
          </span>
        </div>
      </motion.div>

      {/* Workflow Info */}
      <Card>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-400 mb-1">Topic</p>
            <p className="font-semibold">{content.metadata.topic}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-1">Audience</p>
            <p className="font-semibold capitalize">
              {content.metadata.audience}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-1">Duration</p>
            <p className="font-semibold">
              {content.metadata.duration_seconds}s
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-1">Cost</p>
            <p className="font-semibold">
              ${content.metadata.cost_usd.toFixed(2)}
            </p>
          </div>
        </div>

        {content.supervisor_decision && (
          <div className="mt-4 pt-4 border-t border-gray-700">
            <p className="text-xs text-gray-400 mb-2">Supervisor Reasoning</p>
            <p className="text-sm text-gray-300">
              {content.supervisor_decision.reasoning}
            </p>
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 bg-gray-700 rounded-full h-2 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{
                    width: `${content.supervisor_decision.confidence * 100}%`,
                  }}
                  className="h-full bg-gradient-to-r from-primary-500 to-secondary-500"
                />
              </div>
              <span className="text-xs font-semibold">
                {Math.round(content.supervisor_decision.confidence * 100)}%
                confidence
              </span>
            </div>
          </div>
        )}
      </Card>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Video Preview */}
        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Video className="w-5 h-5 text-primary-400" />
              Video Preview
            </h2>
            <Button
              size="sm"
              variant="outline"
              onClick={() => window.open(content.video_url)}
            >
              <Download className="w-4 h-4" />
            </Button>
          </div>

          {/* Video Player */}
          <div className="relative aspect-[9/16] bg-gray-900 rounded-lg overflow-hidden max-w-sm mx-auto">
            <video
              src={content.video_url}
              className="w-full h-full object-cover"
              controls
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            />
            {!isPlaying && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="absolute inset-0 flex items-center justify-center bg-black/30"
              >
                <Play className="w-16 h-16 text-white" />
              </motion.div>
            )}
          </div>

          {/* Platform Selector */}
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={selectedPlatform === 'tiktok' ? 'primary' : 'outline'}
              onClick={() => setSelectedPlatform('tiktok')}
              className="flex-1"
            >
              TikTok
            </Button>
            <Button
              size="sm"
              variant={
                selectedPlatform === 'youtube_shorts' ? 'primary' : 'outline'
              }
              onClick={() => setSelectedPlatform('youtube_shorts')}
              className="flex-1"
            >
              YouTube Shorts
            </Button>
          </div>
        </Card>

        {/* Script & Metadata */}
        <div className="space-y-4">
          {/* Script */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary-400" />
                Video Script
              </h2>
              <Eye className="w-4 h-4 text-gray-400" />
            </div>
            <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto">
              <pre className="text-sm text-gray-300 whitespace-pre-wrap font-sans">
                {content.script}
              </pre>
            </div>
          </Card>

          {/* Platform Metadata */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Hash className="w-5 h-5 text-primary-400" />
                {selectedPlatform === 'tiktok' ? 'TikTok' : 'YouTube'} Metadata
              </h2>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsEditing(!isEditing)}
              >
                <Edit3 className="w-4 h-4" />
              </Button>
            </div>

            <AnimatePresence mode="wait">
              {isEditing ? (
                <motion.div
                  key="editing"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-4"
                >
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">
                      Title
                    </label>
                    <input
                      type="text"
                      value={editedMetadata.title || platformData?.title || ''}
                      onChange={(e) =>
                        setEditedMetadata({
                          ...editedMetadata,
                          title: e.target.value,
                        })
                      }
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">
                      Description
                    </label>
                    <textarea
                      value={
                        editedMetadata.description ||
                        platformData?.description ||
                        ''
                      }
                      onChange={(e) =>
                        setEditedMetadata({
                          ...editedMetadata,
                          description: e.target.value,
                        })
                      }
                      rows={6}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary-500 resize-none"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">
                      Hashtags
                    </label>
                    <input
                      type="text"
                      value={
                        editedMetadata.hashtags?.join(', ') ||
                        platformData?.hashtags?.join(', ') ||
                        ''
                      }
                      onChange={(e) =>
                        setEditedMetadata({
                          ...editedMetadata,
                          hashtags: e.target.value
                            .split(',')
                            .map((h) => h.trim()),
                        })
                      }
                      placeholder="Separate with commas"
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary-500"
                    />
                  </div>

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={handleSaveEdits}
                      className="flex-1"
                    >
                      Save Changes
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setIsEditing(false)}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="viewing"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-4"
                >
                  <div>
                    <p className="text-xs text-gray-400 mb-1">Title</p>
                    <p className="text-sm font-semibold">
                      {platformData?.title}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-gray-400 mb-1">Description</p>
                    <p className="text-sm text-gray-300 whitespace-pre-wrap">
                      {platformData?.description}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-gray-400 mb-1">Hashtags</p>
                    <div className="flex flex-wrap gap-2">
                      {platformData?.hashtags?.map((tag, i) => (
                        <span
                          key={i}
                          className="px-2 py-1 bg-primary-500/20 text-primary-400 rounded text-xs"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </Card>
        </div>
      </div>

      {/* Action Buttons */}
      <Card>
        <div className="flex flex-col md:flex-row gap-4">
          <Button
            size="lg"
            onClick={handleApprove}
            className="flex-1 gap-2"
            disabled={content.status !== 'pending_review'}
          >
            <ThumbsUp className="w-5 h-5" />
            Approve & Publish
          </Button>

          <Button
            size="lg"
            variant="outline"
            onClick={handleRegenerate}
            className="flex-1 gap-2"
          >
            <RefreshCw className="w-5 h-5" />
            Regenerate
          </Button>

          <Button
            size="lg"
            variant="outline"
            onClick={handleReject}
            className="flex-1 gap-2 border-red-500/50 text-red-400 hover:bg-red-500/10"
            disabled={content.status !== 'pending_review'}
          >
            <ThumbsDown className="w-5 h-5" />
            Reject
          </Button>
        </div>

        <p className="text-xs text-gray-400 text-center mt-4">
          {content.status === 'pending_review'
            ? 'Review the content carefully before approving. Once published, the video will be uploaded to the selected platforms.'
            : 'This content has already been processed.'}
        </p>
      </Card>
    </div>
  );
}
