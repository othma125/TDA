import math
from haversine import haversine

class location:
    def __init__(self, line: list[str]):
        self.index: int = int(line[0]) - 1
        self.X: float = float(line[1])
        self.Y: float = float(line[2])
        self.capacity: int = int(line[3])
        self.is_siding: bool = line[4] == 'siding'

    def __str__(self):
        return f'Location with index = {self.index + 1}'


class track:
    def __init__(self, departure: location, arrival: location):
        self.departure_location: location = departure
        self.arrival_location: location = arrival
        self.is_single_track: bool = self.departure_location.is_siding or self.arrival_location.is_siding

    def traveled_time(self, train_speed: int) -> int:
        distance = (self.departure_location.X - self.arrival_location.X) ** 2 + (
                self.departure_location.Y - self.arrival_location.Y) ** 2
        distance: float = math.sqrt(distance)
        departure = (self.departure_location.X, self.departure_location.Y)
        arrival = (self.arrival_location.X, self.arrival_location.Y)
        return int((haversine(departure, arrival) / train_speed) * 60)

    def __str__(self):
        return f'Track(departure = {self.departure_location}, arrival = {self.arrival_location})'


class train:
    def __init__(self, i: int, departure: int, arrival: int, category: int, tracks: list[track], path: list[location]):
        self.index = i
        self.departure_time: int = departure
        self.arrival_time: int = arrival
        self.category: int = category
        self.tracks: list[track] = tracks
        self.path: list[location] = path
        self.departure_location: location = self.path[0]
        self.arrival_location: location = self.path[len(self.path) - 1]

    def __str__(self):
        return f'Index = {self.index + 1} and Category = {self.category}'
