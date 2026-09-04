export interface TripPlanRequest {
  city: string
  start_date: string
  end_date: string
  preferences: string[]
  budget_level: string
  transportation: string
  accommodation: string
}

export interface Location {
  longitude: number
  latitude: number
}

export interface Attraction {
  poi_id: string | null
  name: string
  address: string
  type_code: string | null
  location: Location | null
  description: string
  category: string
  rating: number | null
  visit_duration: number
  ticket_price: number
  image_url: string | null
}

export interface WeatherInfo {
  date: string
  day_weather: string
  night_weather: string | null
  day_temp: number | null
  night_temp: number | null
  wind_direction: string | null
  wind_power: string | null
}

export interface Hotel {
  poi_id: string | null
  name: string
  address: string
  type_code: string | null
  location: Location | null
  rating: number | null
  price_range: string
  distance: string
  hotel_type: string
  estimated_cost_per_night: number
}

export interface Meal {
  poi_id: string | null
  type_code: string | null
  meal_type: string
  name: string
  address: string
  location: Location | null
  description: string
  rating: number | null
  estimated_cost: number
}

export interface DayPlan {
  date: string
  day_index: number
  title: string
  description: string
  attractions: Attraction[]
  meals: Meal[]
  hotel: Hotel | null
  transportation: string
  accommodation: string
  estimated_daily_cost: number
}

export interface Budget {
  attraction_cost: number
  hotel_cost: number
  meal_cost: number
  transportation_cost: number
  total: number
}

export interface TripPlan {
  city: string
  start_date: string
  end_date: string
  days: DayPlan[]
  weather_info: WeatherInfo[]
  overall_suggestions: string
  budget: Budget | null
}

