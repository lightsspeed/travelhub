import { useSearchParams, useNavigate } from 'react-router-dom';
import { MapPin, Star, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const MOCK_RESULTS = [
  {
    id: '1',
    name: 'Grand Horizon Resort',
    location: 'Goa, India',
    rating: 4.8,
    reviews: 124,
    price: 150,
    image: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=400&q=80',
    amenities: ['Pool', 'Spa', 'Free WiFi'],
  },
  {
    id: '4',
    name: 'Sunset Beach Villas',
    location: 'Goa, India',
    rating: 4.2,
    reviews: 89,
    price: 110,
    image: 'https://images.unsplash.com/photo-1582719508461-905c673771fd?auto=format&fit=crop&w=400&q=80',
    amenities: ['Beachfront', 'Restaurant', 'Bar'],
  },
  {
    id: '5',
    name: 'The Palm Retreat',
    location: 'Goa, India',
    rating: 4.5,
    reviews: 210,
    price: 135,
    image: 'https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?auto=format&fit=crop&w=400&q=80',
    amenities: ['Gym', 'Free Breakfast', 'Pool'],
  },
];

export default function Search() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const destination = searchParams.get('dest') || 'Everywhere';

  return (
    <div className="flex flex-col md:flex-row gap-8">
      {/* Filters Sidebar */}
      <div className="w-full md:w-64 space-y-6">
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2 mb-4">
            <Filter className="w-4 h-4" />
            Filters
          </h2>
          <div className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="price-range">Max Price ($)</Label>
              <Input id="price-range" type="number" defaultValue="500" />
            </div>
            <div className="grid gap-2">
              <Label>Minimum Rating</Label>
              <div className="flex gap-2">
                {[3, 4, 4.5].map(rating => (
                  <Badge key={rating} variant="outline" className="cursor-pointer hover:bg-slate-100">
                    {rating}+ <Star className="w-3 h-3 ml-1 fill-current" />
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </div>
        <Button className="w-full">Apply Filters</Button>
      </div>

      {/* Results */}
      <div className="flex-1 space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Search Results for "{destination}"</h1>
          <p className="text-slate-500">{MOCK_RESULTS.length} properties found</p>
        </div>

        <div className="space-y-4">
          {MOCK_RESULTS.map((hotel) => (
            <Card key={hotel.id} className="overflow-hidden flex flex-col sm:flex-row cursor-pointer hover:border-primary/50 transition-colors" onClick={() => navigate(`/hotels/${hotel.id}`)}>
              <div className="sm:w-64 h-48 sm:h-auto shrink-0">
                <img src={hotel.image} alt={hotel.name} className="w-full h-full object-cover" />
              </div>
              <CardContent className="flex-1 p-6 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-xl font-bold">{hotel.name}</h3>
                    <div className="text-right">
                      <div className="text-lg font-bold">${hotel.price}</div>
                      <div className="text-xs text-slate-500">per night</div>
                    </div>
                  </div>
                  <div className="flex items-center text-slate-500 text-sm mb-4">
                    <MapPin className="w-4 h-4 mr-1" />
                    {hotel.location}
                  </div>
                  <div className="flex gap-2 mb-4">
                    {hotel.amenities.map(amenity => (
                      <Badge key={amenity} variant="secondary" className="font-normal">{amenity}</Badge>
                    ))}
                  </div>
                </div>
                
                <div className="flex justify-between items-center mt-4 pt-4 border-t border-slate-100">
                  <div className="flex items-center gap-1">
                    <Star className="w-4 h-4 text-amber-500 fill-current" />
                    <span className="font-medium">{hotel.rating}</span>
                    <span className="text-slate-500 text-sm">({hotel.reviews} reviews)</span>
                  </div>
                  <Button onClick={(e: any) => { e.stopPropagation(); navigate(`/hotels/${hotel.id}`); }}>
                    View Details
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
