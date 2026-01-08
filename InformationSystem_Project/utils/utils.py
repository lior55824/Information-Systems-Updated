from datetime import datetime, timedelta
from abc import ABC, abstractmethod


class Unidentified_Guests:
    """ Represents an unidentified (non-registered) guest user in the system.
        Can search for flights, create bookings, view active tickets using an order code and email, and cancel bookings according to the system rules. """

    def __init__(self, email_address, first_name_in_english, last_name_in_english, phone_numbers=None):
        self.email_address = email_address
        self.first_name_in_english = first_name_in_english
        self.last_name_in_english = last_name_in_english
        if phone_numbers is None:
            self.phone_numbers = []
        else:
            self.phone_numbers = phone_numbers


class RegisteredClient(Unidentified_Guests):
    def __init__(self, email_address, first_name_in_english, last_name_in_english, passport_id, birth_date, password,
                 phone_numbers=None):
        super().__init__(email_address, first_name_in_english, last_name_in_english, phone_numbers)
        self.passport_id = passport_id
        self.birth_date = birth_date
        self.password = password
        self.registration_date = datetime.now()


class Workers(ABC):
    def __init__(self, worker_id, first_name_in_hebrew, last_name_in_hebrew, phone_number, address_city, address_street,
                 address_number, start_date):
        self.worker_id = worker_id
        self.first_name_in_hebrew = first_name_in_hebrew
        self.last_name_in_hebrew = last_name_in_hebrew
        self.phone_number = phone_number
        self.address_city = address_city
        self.address_street = address_street
        self.address_number = address_number
        self.start_date = start_date

    def __str__(self):
        return f"{self.first_name_in_hebrew} {self.last_name_in_hebrew} ({self.worker_id})"


class Managers(Workers):
    def __init__(self, worker_id, first_name_in_hebrew, last_name_in_hebrew, phone_number, address_city, address_street,
                 address_number, start_date, first_name_in_english, last_name_in_english, password):
        # 1. קריאה לבנאי של מחלקת האב כדי לאתחל את השדות המשותפים
        super().__init__(worker_id, first_name_in_hebrew, last_name_in_hebrew, phone_number, address_city,
                         address_street, address_number, start_date)
        # 2. אתחול השדות הייחודיים למנהל
        self.first_name_in_english = first_name_in_english
        self.last_name_in_english = last_name_in_english
        self.password = password

    def __str__(self):
        return f"Manager: {self.first_name_in_english} {self.last_name_in_english} (ID: {self.worker_id})"


class Pilots(Workers):
    def __init__(self, worker_id, first_name_in_hebrew, last_name_in_hebrew, phone_number, address_city, address_street,
                 address_number, start_date, is_long_flight_qualified):
        # קריאה לבנאי של מחלקת האב
        super().__init__(worker_id, first_name_in_hebrew, last_name_in_hebrew, phone_number, address_city,
                         address_street, address_number, start_date)
        # האם עבר הכשרה לטיסות ארוכות? (מקבל True או False)
        self.is_long_flight_qualified = is_long_flight_qualified


class FlightAttendants(Workers):
    def __init__(self, worker_id, first_name_in_hebrew, last_name_in_hebrew, phone_number, address_city, address_street,
                 address_number, start_date, is_long_flight_qualified):
        # קריאה לבנאי של מחלקת האב
        super().__init__(worker_id, first_name_in_hebrew, last_name_in_hebrew, phone_number, address_city,
                         address_street, address_number, start_date)
        # האם עבר הכשרה לטיסות ארוכות?
        self.is_long_flight_qualified = is_long_flight_qualified


class Seat(ABC):
    def __init__(self, row_number, column_number):
        self.row_number = row_number
        self.column_number = column_number

    @abstractmethod
    def get_price(self, flight):
        pass

    @property
    @abstractmethod
    def seat_type(self):
        pass

    def __str__(self):
        return f"Row {self.row_number}, Col {self.column_number} ({self.seat_type})"

    def __repr__(self):
        return f"{self.seat_type}Seat({self.row_number}, {self.column_number})"

class EconomySeat(Seat):
    def get_price(self, flight):
        return flight.economy_price

    @property
    def seat_type(self):
        return "Economy"

class BusinessSeat(Seat):
    def get_price(self, flight):
        return flight.business_price

    @property
    def seat_type(self):
        return "Business"

    def __repr__(self):
        return f"Seat(row={self.row_number}, col={self.column_number})"


class Plane:
    def __init__(self, plane_id, manufacturer, plane_size, purchase_date, seats):
        self.plane_id = plane_id
        self.manufacturer = manufacturer
        self.plane_size = plane_size
        self.purchase_date = purchase_date
        if not seats or len(seats) == 0:
            raise ValueError("A plane cannot be created without seats.")
        self.seats = seats

    def can_fly_long(self):
        return self.plane_size == "large"

    def __str__(self):
        return f"Plane {self.plane_id}: {self.manufacturer} ({len(self.seats)} seats)"


class Flight:
    """ Represents a flight in the system."""

    def __init__(self, flight_id, plane_id, origin, destination, departure_time, departure_date, duration_minutes, economy_price, business_price):
        self.flight_id = flight_id
        self.plane_id = plane_id
        self.origin = origin
        self.destination = destination
        self.departure_time = departure_time
        self.departure_date = departure_date
        self.duration_minutes = duration_minutes
        self.economy_price = economy_price
        self.business_price = business_price

        self._occupied_seats = set()
        # self.status = "active"  Initial status of a newly created flight, need to check if this is neccesary

    def is_seat_available(self, seat):
        return seat not in self._occupied_seats

    def book_seats(self, seats_to_book):
        for seat in seats_to_book:
            if seat in self._occupied_seats:
                raise ValueError(f"Error: Seat {seat} is already occupied on flight {self.flight_id}.")
        for seat in seats_to_book:
            self._occupied_seats.add(seat)
            print(f"DEBUG: Seat {seat} was successfully marked as occupied.")

    def release_seats(self, seats_to_release):
        for seat in seats_to_release:
            if seat in self._occupied_seats:
                self._occupied_seats.remove(seat)
                print(f"DEBUG: Seat {seat} is now free.")

    def get_departure_datetime(self):  # Returns the flight departure date and time as a single datetime object
        return datetime.combine(self.departure_date, self.departure_time)

    def get_arrival_datetime(self):  # Calculates and returns the flight arrival date and time.
        duration = timedelta(minutes=self.duration_minutes)  # Create timedelta object for flight duration
        arrival_datetime = self.get_departure_datetime() + duration  # Calculate arrival datetime
        return arrival_datetime

    def is_short_flight(
            self):  # Checks whether the flight is considered a short flight. A flight is classified as short if its duration is up to 6 hours (360 minutes)
        return self.duration_minutes <= 360


class Order:
    def __init__(self, order_code, flight, customer, seats):
        self.order_code = order_code
        self.flight = flight
        self.customer = customer
        self.seats = seats
        self.status = "active"
        self.created_at = datetime.now()
        self.total_price = self.calculate_total_price()
        self.flight.book_seats(self.seats)

    def calculate_total_price(self):
        total = 0
        for seat in self.seats:
            total += seat.get_price(self.flight)
        return total

    def cancel_order(self):
        if self.status == "canceled":
            return
        self.status = "canceled"
        self.flight.release_seats(self.seats)
        self.total_price *= 0.95  # Cancellation fee logic
        print(f"Order {self.order_code} canceled. Price adjusted.")