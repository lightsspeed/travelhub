import { Link } from 'react-router-dom';
import { PlaneTakeoff, MessageSquare, BookOpen, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function Navbar() {
  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <Link to="/" className="flex items-center space-x-2 text-primary font-bold text-xl">
            <PlaneTakeoff className="h-6 w-6" />
            <span>TravelHub</span>
          </Link>
          <div className="flex space-x-2 items-center">
            <Link to="/search">
              <Button variant="ghost" size="sm">
                <Search className="w-4 h-4 mr-2" />
                Explore
              </Button>
            </Link>
            <Link to="/bookings">
              <Button variant="ghost" size="sm">
                <BookOpen className="w-4 h-4 mr-2" />
                My Bookings
              </Button>
            </Link>
            <Link to="/assistant">
              <Button variant="default" size="sm">
                <MessageSquare className="w-4 h-4 mr-2" />
                AI Assistant
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
