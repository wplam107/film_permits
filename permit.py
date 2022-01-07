import re
from datetime import datetime

class Permit(object):
    __slots__ = [
        'eventid', 'startdatetime', 'enddatetime',
        'parkingheld', 'borough', 'category',
        'subcategoryname', 'zipcode_s', 'points',
        'linestrings'
    ]

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.__slots__:
                setattr(self, key, value.lower())
        
        self._clean_address()
        self._cap_boro()
        self._get_intersections()
        self._get_datetime()

        self.points = []
        self.linestrings = []


    # Initialization Data Processing
    def _cap_boro(self):
        """
        Method to capitalize borough.
        """
        self.borough = self.borough.capitalize()

    def _clean_address(self):
        """
        Method to clean and split parking address string.

        Example: convert 'A between B and C, X between Y and Z'
        to ['A Between B And C', 'X Between Y And Z']
        """
        list_of_spots = self.parkingheld.split(', ')
        split_list = [ ' '.join([ word.capitalize() for word in s.split() ]) for s in list_of_spots ]
        self.parkingheld = split_list

    def _ordinal_rep(self, s: str) -> str:
        """
        Helper function to convert numerical cardinality to ordinality.
        """
        num = re.search(r'[0-9]+\s', s)
        if num == None:
            return s
        else:
            num = re.search(r'[0-9]+', s)[0]
            if len(num) > 1:
                if (num[-1] == '1') and (num[-2] != '1'):
                    ord = num + 'st'
                elif num[-1] == '2' and (num[-2] != '1'):
                    ord = num + 'nd'
                elif num[-1] == '3' and (num[-2] != '1'):
                    ord = num + 'rd'
                else:
                    ord = num + 'th'
            else:
                if (num[-1] == '1'):
                    ord = num + 'st'
                elif num[-1] == '2':
                    ord = num + 'nd'
                elif num[-1] == '3':
                    ord = num + 'rd'
                else:
                    ord = num + 'th'
            return s.replace(num, ord)

    def _abb_to_full(self, street: str) -> str:
        """
        Helper function to convert cardinality abbreviation to full.
        """
        if 'W ' in street:
            street = 'West ' + street.split('W ')[1]
        if 'E ' in street:
            street = 'East ' + street.split('E ')[1]
        if 'N ' in street:
            street = 'North ' + street.split('N ')[1]
        if 'S ' in street:
            street = 'South ' + street.split('S ')[1]
        return street

    def _clean_street(self, street: str) -> str:
        """
        Method to standardize street names.
        """
        if ' St' in street:
            street = street.split(' St')[0] + ' Street'
        if ' Ave' in street:
            street = street.split(' Ave')[0] + ' Avenue'
        if ' Rd' in street:
            street = street.split(' Rd')[0] + ' Road'
        if ' Pkwy' in street:
            street = street.split(' Pkwy')[0] + ' Parkway'
        if ' Blvd' in street:
            street = street.split(' Blvd')[0] + ' Boulevard'
        
        street = self._abb_to_full(street)
        street = self._ordinal_rep(street)
        return street    

    def _get_intersections(self):
        """
        Method to process string of parking held to intersection points.
        """
        list_of_intersec = []
        null_streets = ['Dead Road', 'Dead End', 'Dead Rd']
        for street in self.parkingheld:
            null_st = False
            for s in null_streets:
                if s in street:
                    null_st = True
            if null_st == True:
                pass
            else:
                block = street.split(' Between ')
                if len(block) != 2:
                    pass
                else:
                    main_st = self._clean_street(block[0])
                    cross_st = block[1].split(' And ')
                    st_names = [main_st] + cross_st
                    if len(st_names) != 3:
                        pass
                    else:
                        try:
                            if self.borough == 'Manhattan':
                                boro = 'New York'
                            else:
                                boro = self.borough
                            p1 = sorted([main_st, self._clean_street(cross_st[0])]) + [boro]
                            p2 = sorted([main_st, self._clean_street(cross_st[1])]) + [boro]
                            interdict = {
                                'point1': (tuple(p1)),
                                'point2': (tuple(p2))
                            }
                            list_of_intersec.append(interdict)
                        except:
                            pass
        self.parkingheld = list_of_intersec

    def _get_datetime(self):
        """
        Method to convert datetime string to datetime object.
        """
        sdt = ' '.join(self.startdatetime.split('t'))
        sdt = sdt.split('.')[0]
        edt = ' '.join(self.enddatetime.split('t'))
        edt = edt.split('.')[0]
        dt_str = '%Y-%m-%d %H:%M:%S'
        self.startdatetime = datetime.strptime(sdt, dt_str)
        self.enddatetime = datetime.strptime(edt, dt_str)

    # For creating a list of distinct intersections to geocode
    def list_intersections(self) -> list[str]:
        """
        Returns a list of intersections.
        """
        intersections = []
        for ps in self.parkingheld:
            intersections.append(ps['point1'])
            intersections.append(ps['point2'])
        return list(set(intersections))
