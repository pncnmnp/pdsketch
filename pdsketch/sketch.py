from collections import defaultdict
from os import sendfile
from posixpath import dirname
from pdsketch import Diagram, PDPoint
from greedypermutation.clarksongreedy import greedy

class Sketch:
    """
    A class to generate sketches from a persistence diagram.
    The class has two members, both internal: `_state` and `_sketches`.
    `_sketches` is a List where each element is a tuple of the form `(point, parent_index, transportation_plan)` which represents a sketch.
    `_state` points to the element of `_sketches` in memory.
    A particular sketch can be accessed by indexing.
    """
    def __init__(self, D: Diagram, n: int = None):
        """
        Parameters
        ----------
        D : Diagram
            The PD to be sketched
        n : int
            The number of sketches to be produced
        """
        # If `n` is not passed as a parameter, compute sketches for all `D/2` off-diagonal points.
        if not n:
            n = len(D)//2
        sketches = greedy(M=D, seed=D[-1], nbrconstant=2, tree=True, gettransportplan=True)
        mass = defaultdict(int)
        # `mass` is a transportation plan for the current sketch.
        # The reason we need to modify the transportation plan generated by `clarksongreedy` is that `clarksongreedy` treats all diagonal points as distinct.
        # In `mass` the multiplicity of all diagonal points in the sketch is moved to a single key, (0,0).
        i = 0
        self._sketches = []
        diagonal = PDPoint([0,0])
        mass[diagonal] = -len(D)//2
        # The above line rectifies the incorrect multplicity that would be added by diagonal projections.
        while i <= n:
            curr_sketch = next(sketches)
            for p in curr_sketch[2]:
                if D.isdiagonalpoint(p):
                    mass[diagonal] += curr_sketch[2][p]
                else:
                    mass[p] += curr_sketch[2][p]
            if i == 0 or not D.isdiagonalpoint(curr_sketch[0]):
                # The above condition ensures that only off-diagonal points are added to the sketch except for the 0th sketch which is just the diagonal.
                # So we end up with `n` off-diagonal points.
                self._sketches.append((curr_sketch[0], curr_sketch[1], mass.copy()))
                mass.clear()
                i += 1
            
        self._state = {'index': 0, 'mass': defaultdict(int, self._sketches[0][2])}

    def __getitem__(self, index)->defaultdict:
        """
        Return sketch accessed by index.
        """
        # Different approach when slicing??
        if isinstance(index, slice):
            # return a generator which can iterate over the requested sketches
            indices = range(index.start, index.stop, index.step)
            return (self._sketches[i] for i in indices)
        else:
            # fetch self._sketches[index]
            sign = 1 if index >= self._state['index'] else -1
            while index != self._state['index']:
                self._updateState(sign)
            return self._state['mass']

    def __iter__(self):
        """
        Returns an iterator on the sketches.
        """
        return iter(self._sketches)

    def __hash__(self) -> int:
        return hash(tuple(self._sketches))
    
    def _updateState(self, sign):
        """
        Internal method to move from one sketch to another.
        Moves the current sketch in memory to one forward or backward depending on `sign`.
        """
        self._state['index'] += sign
        transport = self._sketches[self._state['index']][2]
        for p in transport:
            self._state['mass'][p] += sign*transport[p]
        
    def _dict(self, str_transport: str):
        """
        Internal method to convert string to transportation plan.
        Used only in method `savetofile()`.
        """
        transport = defaultdict(int)
        str_transport = str_transport[str_transport.find('{')+1:str_transport.find('}')]
        dict_entries = str_transport.split(", ")
        for entry in dict_entries:
            key_value = entry.split(": ")
            transport[PDPoint([float(p) for p in key_value[0].split()])] = int(key_value[1])
        return transport
    
    def loadfromfile(self, filename:str):
        """
        Clears current sketches and loads sketches from a previously saved text file.

        File format: Should be a text file with the ith line as follows:
        b_i d_i; parent_i; transportplan_i
        where (b_i, d_i) is the ith point added to the sketch, parent_i is its parent
        and transportplan_i is the ith transportation plan in defaultdict(int) format.
        """
        self._sketches.clear()
        with open(filename+'.txt', 'r') as s:
            for sketch in s:
                elements = sketch.rstrip().split("; ")
                point = PDPoint([float(p) for p in elements[0].split()])
                parent = int(elements[1]) if elements[1] != 'None' else None
                transport = self._dict(elements[2])
                self._sketches.append((point, parent, transport))
        self._state['index'] = 0
        self._state['mass'] = defaultdict(int, self._sketches[0][2])

    def savetofile(self, filename:str = "sketch"):
        """
        Save current sketches to a text file.
        The ith line will be saved as follows:
        b_i d_i; parent_i; transportplan_i
        where (b_i, d_i) is the ith point added to the sketch, parent_i is the index of its
        parent and transportplan_i is the ith transportation plan in defaultdict(int) format.
        """
        # Move `_state` to beginning
        self._state['index'] = 0
        self._state['mass'] = defaultdict(int, self._sketches[0][2])
        with open(filename+'.txt', 'w') as s:
            for i in range(len(self._sketches)):
                s.write("; ".join(str(self._sketches[i][j]) for j in range(3))+"\n")