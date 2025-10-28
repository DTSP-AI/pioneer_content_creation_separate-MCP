import { motion } from 'framer-motion';
import { TrendingUp } from 'lucide-react';
import { useWorkflowStore } from '../store/workflow';
import Card from '../components/Card';
import Button from '../components/Button';

export default function Dashboard() {
  const { workflows } = useWorkflowStore();

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center space-y-4"
      >
        <h1 className="text-4xl font-bold gradient-text">
          AI-Powered Content Creation
        </h1>
        <p className="text-xl text-gray-400 max-w-2xl mx-auto">
          Create viral TikTok and YouTube Shorts videos with intelligent AI
          agents. From script to publishing in minutes.
        </p>
      </motion.div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-primary-500/20 rounded-lg">
              <TrendingUp className="w-6 h-6 text-primary-400" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Total Workflows</p>
              <p className="text-2xl font-bold">{workflows.length}</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-500/20 rounded-lg">
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ repeat: Infinity, duration: 2 }}
              >
                ✅
              </motion.div>
            </div>
            <div>
              <p className="text-sm text-gray-400">Completed</p>
              <p className="text-2xl font-bold">
                {
                  workflows.filter((w) => w.workflow_status === 'completed')
                    .length
                }
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-secondary-500/20 rounded-lg">💰</div>
            <div>
              <p className="text-sm text-gray-400">Total Cost</p>
              <p className="text-2xl font-bold">
                $
                {workflows
                  .reduce((sum, w) => sum + (w.total_cost_usd || 0), 0)
                  .toFixed(2)}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Create Workflow Button */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="flex justify-center"
      >
        <Button
          size="lg"
          onClick={() => alert('Workflow creation coming soon!')}
          className="gap-3"
        >
          <span className="text-xl">+</span>
          Create New Workflow
        </Button>
      </motion.div>

      {/* Pending Reviews Section */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Pending Reviews</h2>
        <Card className="hover:shadow-lg transition-shadow">
          <div className="flex flex-col md:flex-row md:items-center gap-4">
            <div className="flex-1">
              <h3 className="text-lg font-semibold mb-2">
                AI Content Creation Tips Video
              </h3>
              <p className="text-sm text-gray-400 mb-3">
                Created for TikTok & YouTube Shorts • 45s • Educational Style
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded text-xs">
                  Pending Review
                </span>
                <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs">
                  $0.42 cost
                </span>
                <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded text-xs">
                  89% confidence
                </span>
              </div>
            </div>
            <Button onClick={() => (window.location.href = '/chat')}>
              Create Content →
            </Button>
          </div>
        </Card>
      </div>

      {/* Recent Workflows */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Recent Workflows</h2>
        <Card className="text-center py-12">
          <p className="text-gray-400 mb-4">
            No completed workflows yet. Start by reviewing pending content!
          </p>
          <Button onClick={() => alert('Create workflow feature coming soon!')}>
            Create New Workflow
          </Button>
        </Card>
      </div>
    </div>
  );
}
