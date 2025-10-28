import { Link } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-dark-950 flex flex-col">
      {/* Header - Responsive visibility */}
      <header className="sticky top-0 z-40 glass border-b border-dark-800 flex-shrink-0">
        <div className="container mx-auto px-4 md:px-6 py-3 md:py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2 md:gap-3">
              <h1 className="text-lg md:text-xl font-bold gradient-text">
                Content Creation Agent
              </h1>
            </Link>
            <nav
              className="flex items-center gap-2 md:gap-4"
              aria-label="Main navigation"
            >
              <Link
                to="/"
                className="text-sm md:text-base text-gray-400 hover:text-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 rounded px-2 py-1"
                aria-label="Go to Dashboard"
              >
                Dashboard
              </Link>
              <Link
                to="/chat"
                className="text-sm md:text-base text-gray-400 hover:text-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 rounded px-2 py-1"
                aria-label="Go to Chat"
              >
                Chat
              </Link>
              <Link
                to="/chat"
                className="hidden sm:inline text-sm md:text-base text-gray-400 hover:text-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 rounded px-2 py-1"
                aria-label="Chat"
              >
                Chat
              </Link>
              <a
                href="http://localhost:8006/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="hidden md:inline text-sm text-gray-400 hover:text-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 rounded px-2 py-1"
                aria-label="View API Documentation"
              >
                API Docs
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 md:px-6 py-6 md:py-8 flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer
        className="border-t border-dark-800 mt-auto flex-shrink-0"
        role="contentinfo"
      >
        <div className="container mx-auto px-4 md:px-6 py-4 md:py-6 text-center text-xs md:text-sm text-gray-500">
          <p>Content Creation Agent v3.0.0 | Port 3006 | Backend: 8006</p>
        </div>
      </footer>
    </div>
  );
}
