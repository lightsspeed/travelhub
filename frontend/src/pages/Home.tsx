import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, MapPin, Calendar, Users, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const FEATURED_HOTELS = [
  {
    id: '1',
    name: 'Grand Horizon Resort',
    location: 'Goa, India',
    rating: 4.8,
    price: 150,
    image: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80',
  },
  {
    id: '2',
    name: 'Mountain View Lodge',
    location: 'Manali, India',
    rating: 4.6,
    price: 85,
    image: 'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=800&q=80',
  },
  {
    id: '3',
    name: 'Urban Oasis Hotel',
    location: 'Mumbai, India',
    rating: 4.5,
    price: 120,
    image: 'https://images.unsplash.com/photo-1551882547-ff40c0d5b9af?auto=format&fit=crop&w=800&q=80',
  },
];

export default function Home() {
  const navigate = useNavigate();
  const [destination, setDestination] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (destination) {
      navigate(`/search?dest=${encodeURIComponent(destination)}`);
    } else {
      navigate('/search');
    }
  };

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="relative rounded-2xl overflow-hidden h-[400px] flex items-center justify-center">
        <div className="absolute inset-0 z-0">
          <img 
            src="https://images.unsplash.com/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&w=2000&q=80" 
            alt="Travel Hero" 
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-black/40" />
        </div>
        
        <div className="relative z-10 w-full max-w-4xl mx-auto px-4 text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Find your next perfect stay.
          </h1>
          
          <Card className="p-2 border-0 shadow-lg">
            <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4 items-end">
              <div className="grid w-full items-center gap-1.5 flex-1 text-left">
                <Label htmlFor="destination">Destination</Label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <Input 
                    id="destination" 
                    placeholder="Where are you going?" 
                    className="pl-9"
                    value={destination}
                    onChange={(e: any) => setDestination(e.target.value)}
                  />
                </div>
              </div>
              <div className="grid w-full items-center gap-1.5 flex-1 text-left">
                <Label htmlFor="dates">Dates</Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <Input id="dates" type="text" placeholder="Check in - Check out" className="pl-9" />
                </div>
              </div>
              <div className="grid w-full md:w-32 items-center gap-1.5 text-left">
                <Label htmlFor="guests">Guests</Label>
                <div className="relative">
                  <Users className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <Input id="guests" type="number" min="1" defaultValue="2" className="pl-9" />
                </div>
              </div>
              <Button type="submit" size="lg" className="w-full md:w-auto">
                <Search className="w-4 h-4 mr-2" />
                Search
              </Button>
            </form>
          </Card>
        </div>
      </section>

      {/* Featured Hotels */}
      <section>
        <h2 className="text-2xl font-bold mb-6">Featured Destinations</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {FEATURED_HOTELS.map((hotel) => (
            <Card key={hotel.id} className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer" onClick={() => navigate(`/hotels/${hotel.id}`)}>
              <div className="h-48 overflow-hidden">
                <img src={hotel.image} alt={hotel.name} className="w-full h-full object-cover transition-transform hover:scale-105" />
              </div>
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <CardTitle className="text-lg">{hotel.name}</CardTitle>
                  <Badge variant="secondary" className="flex items-center gap-1">
                    <Star className="w-3 h-3 fill-current" />
                    {hotel.rating}
                  </Badge>
                </div>
                <CardDescription className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {hotel.location}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-500 line-clamp-2">
                  Experience luxury and comfort at our top-rated properties.
                </p>
              </CardContent>
              <CardFooter className="pt-0">
                <div className="text-lg font-bold">
                  ${hotel.price} <span className="text-sm font-normal text-slate-500">/ night</span>
                </div>
              </CardFooter>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
