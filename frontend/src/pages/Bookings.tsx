import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Calendar, MapPin, Users } from 'lucide-react';

type BookingType = {
  id: string;
  hotelName: string;
  location: string;
  dates: string;
  room: string;
  guests: number;
  price: number;
  status: string;
  image: string;
};

const UPCOMING_BOOKINGS = [
  {
    id: 'b1',
    hotelName: 'Grand Horizon Resort',
    location: 'Goa, India',
    dates: 'Oct 15 - Oct 18, 2026',
    room: 'Deluxe Ocean View',
    guests: 2,
    price: 450,
    status: 'Confirmed',
    image: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=400&q=80',
  }
];

const PAST_BOOKINGS = [
  {
    id: 'b2',
    hotelName: 'Urban Oasis Hotel',
    location: 'Mumbai, India',
    dates: 'Jan 10 - Jan 12, 2026',
    room: 'Standard Room',
    guests: 1,
    price: 240,
    status: 'Completed',
    image: 'https://images.unsplash.com/photo-1551882547-ff40c0d5b9af?auto=format&fit=crop&w=400&q=80',
  }
];

export default function Bookings() {
  const renderBooking = (booking: BookingType) => (
    <Card key={booking.id} className="overflow-hidden flex flex-col sm:flex-row mb-4">
      <div className="sm:w-48 h-32 sm:h-auto shrink-0">
        <img src={booking.image} alt={booking.hotelName} className="w-full h-full object-cover" />
      </div>
      <CardContent className="flex-1 p-4 flex flex-col justify-between">
        <div>
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-lg font-bold">{booking.hotelName}</h3>
            <Badge variant={booking.status === 'Confirmed' ? 'default' : 'secondary'}>
              {booking.status}
            </Badge>
          </div>
          <div className="flex items-center text-slate-500 text-sm mb-2">
            <MapPin className="w-4 h-4 mr-1" />
            {booking.location}
          </div>
          <div className="flex gap-4 text-sm text-slate-600 mb-2">
            <span className="flex items-center"><Calendar className="w-4 h-4 mr-1" /> {booking.dates}</span>
            <span className="flex items-center"><Users className="w-4 h-4 mr-1" /> {booking.guests} Guests</span>
          </div>
          <p className="text-sm font-medium">Room: {booking.room}</p>
        </div>
        <div className="text-right mt-2 sm:mt-0 font-bold">
          Total: ${booking.price}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <h1 className="text-3xl font-bold">My Bookings</h1>

      <section>
        <h2 className="text-xl font-bold mb-4">Upcoming</h2>
        {UPCOMING_BOOKINGS.length > 0 ? (
          UPCOMING_BOOKINGS.map(renderBooking)
        ) : (
          <Card className="p-8 text-center text-slate-500">
            <p>You have no upcoming bookings.</p>
          </Card>
        )}
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4">Past Bookings</h2>
        {PAST_BOOKINGS.length > 0 ? (
          PAST_BOOKINGS.map(renderBooking)
        ) : (
          <Card className="p-8 text-center text-slate-500">
            <p>You have no past bookings.</p>
          </Card>
        )}
      </section>
    </div>
  );
}
