import { motion } from 'framer-motion'
import { CheckCircle2, XCircle, Clock, Loader2, AlertTriangle } from 'lucide-react'
import { cn } from '../lib/utils'
import type { WorkflowStatus } from '../types'

interface StatusBadgeProps {
  status: WorkflowStatus | string
  showIcon?: boolean
  className?: string
}

interface StatusConfig {
  icon: typeof CheckCircle2
  label: string
  color: string
  animate?: boolean
}

const statusConfig: Record<string, StatusConfig> = {
  pending: {
    icon: Clock,
    label: 'Pending',
    color: 'text-yellow-400 bg-yellow-500/10',
  },
  pending_review: {
    icon: Clock,
    label: 'Pending Review',
    color: 'text-yellow-400 bg-yellow-500/10',
  },
  running: {
    icon: Loader2,
    label: 'Running',
    color: 'text-blue-400 bg-blue-500/10',
    animate: true,
  },
  completed: {
    icon: CheckCircle2,
    label: 'Completed',
    color: 'text-green-400 bg-green-500/10',
  },
  approved: {
    icon: CheckCircle2,
    label: 'Approved',
    color: 'text-green-400 bg-green-500/10',
  },
  published: {
    icon: CheckCircle2,
    label: 'Published',
    color: 'text-green-400 bg-green-500/10',
  },
  failed: {
    icon: XCircle,
    label: 'Failed',
    color: 'text-red-400 bg-red-500/10',
  },
  rejected: {
    icon: XCircle,
    label: 'Rejected',
    color: 'text-red-400 bg-red-500/10',
  },
  partial_success: {
    icon: AlertTriangle,
    label: 'Partial Success',
    color: 'text-orange-400 bg-orange-500/10',
  },
}

export default function StatusBadge({ status, showIcon = true, className }: StatusBadgeProps) {
  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <motion.div
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium',
        config.color,
        className
      )}
    >
      {showIcon && (
        <Icon
          className={cn('w-4 h-4', config.animate && 'animate-spin')}
        />
      )}
      {config.label}
    </motion.div>
  )
}
