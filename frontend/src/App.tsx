import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/layout/Navbar';
import Home from './pages/Home';
import Search from './pages/Search';
import HotelDetails from './pages/HotelDetails';
import Bookings from './pages/Bookings';
import Assistant from './pages/Assistant';

function App() {
  return (
    <Router>
      <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
        <Navbar />
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/search" element={<Search />} />
            <Route path="/hotels/:id" element={<HotelDetails />} />
            <Route path="/bookings" element={<Bookings />} />
            <Route path="/assistant" element={<Assistant />} />
          </Routes>
        </main>
        <footer className="bg-white border-t border-slate-200 py-8 text-center text-slate-500 text-sm">
          <p>© 2026 TravelHub Educational Project. No real bookings are processed.</p>
        </footer>
      </div>
    </Router>
  );
}

export default App;
