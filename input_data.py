from data_objects import train, track, location


class data:
    def __init__(self, file_name: str):
        """
        Input file reader method
        :param file_name:
        """
        with open("instances\\" + file_name, "r") as file:
            line = file.readline().split()
            self.time_step: int = 5  # minutes
            self.stations_count: int = int(line[0])
            self.locations = [location(file.readline().split()) for _ in range(self.stations_count)]
            line = file.readline().split()
            self.trains_count: int = int(line[0])
            self.trains_speed: int = int(line[1])
            self.trains_waiting_time_in_stations: int = int(line[2])
            self.trains: list[train] = []
            for t in range(self.trains_count):
                line = file.readline().split()
                category: int = int(line[1])
                n: int = len(line)
                departure: int = 0
                time = line[2].split(':')
                departure += int(time[0]) * 60
                departure += int(time[1])
                route: list[location] = [self.locations[int(line[i]) - 1] for i in range(3, n)]
                if len(route) < 2:
                    raise ValueError('train route must contains at least two stop stations')
                tracks = []
                arrival: int = departure
                n: int = len(route)
                for i in range(n - 1):
                    tr = track(route[i], route[i + 1])
                    arrival += tr.traveled_time(self.trains_speed)
                    if not route[i].is_siding:
                        arrival += self.trains_waiting_time_in_stations if i > 0 else 0
                    tracks.append(tr)
                self.trains.append(train(t, departure, arrival, category, tracks, route))


