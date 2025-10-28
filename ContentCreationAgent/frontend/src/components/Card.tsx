import { motion } from 'framer-motion'
import { cn } from '../lib/utils'

interface CardProps {
  children: React.ReactNode
  className?: string
  animate?: boolean
}

export default function Card({ children, className, animate = true }: CardProps) {
  if (!animate) {
    return (
      <div className={cn('glass rounded-xl p-6', className)}>
        {children}
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.01 }}
      className={cn('glass rounded-xl p-6', className)}
    >
      {children}
    </motion.div>
  )
}
