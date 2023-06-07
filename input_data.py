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
                n: int = len(line)
                departure: int = int(line[1])
                category: int = int(line[2])
                path: list[location] = [self.locations[int(line[i]) - 1] for i in range(3, n)]
                tracks = []
                arrival: int = departure
                n: int = len(path)
                for i in range(n - 1):
                    tr = track(path[i], path[i + 1])
                    arrival += tr.traveled_time(self.trains_speed)
                    if not path[i].is_siding:
                        arrival += self.trains_waiting_time_in_stations if i > 0 else 0
                    tracks.append(tr)
                self.trains.append(train(t, departure, arrival, category, tracks, path))


