import { useParams, useNavigate } from 'react-router-dom';
import { MapPin, Star, Wifi, Coffee, Car, Wind } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

const MOCK_HOTEL = {
  id: '1',
  name: 'Grand Horizon Resort',
  location: 'Goa, India',
  rating: 4.8,
  reviews: 124,
  description: 'Experience the ultimate luxury at Grand Horizon Resort. Located right on the pristine beaches, our resort offers world-class amenities, stunning ocean views, and impeccable service. Perfect for both family vacations and romantic getaways.',
  images: [
    'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80',
  ],
  rooms: [
    { id: 'r1', name: 'Deluxe Ocean View', price: 150, capacity: 2, available: true },
    { id: 'r2', name: 'Premium Suite', price: 250, capacity: 4, available: true },
    { id: 'r3', name: 'Standard Room', price: 90, capacity: 2, available: false },
  ]
};

export default function HotelDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const hotel = { ...MOCK_HOTEL, id: id || MOCK_HOTEL.id }; // In reality, fetch based on id

  const handleBook = () => {
    // Placeholder booking flow logic
    navigate('/bookings');
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex justify-between items-start mb-2">
          <h1 className="text-3xl font-bold">{hotel.name}</h1>
          <div className="flex flex-col items-end">
            <div className="flex items-center gap-1 text-lg font-bold">
              <Star className="w-5 h-5 text-amber-500 fill-current" />
              {hotel.rating}
            </div>
            <span className="text-slate-500 text-sm">{hotel.reviews} reviews</span>
          </div>
        </div>
        <div className="flex items-center text-slate-500">
          <MapPin className="w-4 h-4 mr-1" />
          {hotel.location}
        </div>
      </div>

      {/* Image Gallery */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-[400px]">
        <img src={hotel.images[0]} alt="Hotel main" className="w-full h-full object-cover rounded-xl" />
        <div className="hidden md:block">
          <img src={hotel.images[1]} alt="Hotel room" className="w-full h-full object-cover rounded-xl" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-8">
          <section>
            <h2 className="text-xl font-bold mb-4">About this property</h2>
            <p className="text-slate-600 leading-relaxed">{hotel.description}</p>
          </section>

          <section>
            <h2 className="text-xl font-bold mb-4">Amenities</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="flex items-center gap-2 text-slate-600"><Wifi className="w-5 h-5" /> Free WiFi</div>
              <div className="flex items-center gap-2 text-slate-600"><Coffee className="w-5 h-5" /> Breakfast</div>
              <div className="flex items-center gap-2 text-slate-600"><Car className="w-5 h-5" /> Parking</div>
              <div className="flex items-center gap-2 text-slate-600"><Wind className="w-5 h-5" /> AC</div>
            </div>
          </section>
        </div>

        {/* Booking Card */}
        <div className="lg:col-span-1">
          <Card className="sticky top-24">
            <CardHeader>
              <CardTitle>Available Rooms</CardTitle>
              <CardDescription>Select a room to proceed with booking</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {hotel.rooms.map(room => (
                <div key={room.id} className="p-4 border rounded-lg flex flex-col gap-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-semibold">{room.name}</h4>
                      <p className="text-sm text-slate-500">Up to {room.capacity} guests</p>
                    </div>
                    <div className="text-right">
                      <div className="font-bold">${room.price}</div>
                      <div className="text-xs text-slate-500">per night</div>
                    </div>
                  </div>
                  {room.available ? (
                    <Button className="w-full" onClick={handleBook}>Book Now</Button>
                  ) : (
                    <Button variant="secondary" className="w-full" disabled>Sold Out</Button>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
