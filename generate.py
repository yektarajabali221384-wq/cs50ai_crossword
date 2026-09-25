import sys

from crossword import *


class CrosswordCreator:

    def __init__(self, crossword):
        """
        Create a new CSP crossword puzzle.
        """
        self.crossword = crossword

        # Keep track of domains
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]

        for variable, word in assignment.items():
            for k in range(len(variable.cells)):
                i, j = variable.cells[k]
                letters[i][j] = word[k]

        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont

        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border

        letters = self.letter_grid(assignment)

        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )

        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)

        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]

                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")

                    if letters[i][j]:
                        _, _, w, h = draw.textbbox(
                            (0, 0),
                            letters[i][j],
                            font=font
                        )

                        draw.text(
                            (
                                rect[0][0] +
                                ((interior_size - w) / 2),
                                rect[0][1] +
                                ((interior_size - h) / 2) -
                                10
                            ),
                            letters[i][j],
                            fill="black",
                            font=font
                        )

        img.save(filename)

    def enforce_node_consistency(self):
        """
        Enforce node consistency by removing values that violate
        the unary constraint: word length must equal variable length.
        """

        for variable in self.domains:
            self.domains[variable] = {
                word
                for word in self.domains[variable]
                if len(word) == variable.length
            }

    def revise(self, x, y):
        """
        Make variable x arc-consistent with variable y.
        Remove values from x's domain that have no compatible
        value in y's domain.
        """

        revised = False

        overlap = self.crossword.overlaps[x, y]

        if overlap is None:
            return False

        i, j = overlap

        to_remove = set()

        for x_word in self.domains[x]:

            possible = False

            for y_word in self.domains[y]:

                if x_word[i] == y_word[j]:
                    possible = True
                    break

            if not possible:
                to_remove.add(x_word)

        if to_remove:
            self.domains[x] -= to_remove
            revised = True

        return revised

    def ac3(self, arcs=None):
        """
        Enforce arc consistency.

        Return True if arc consistency is achieved and False if
        an empty domain is produced.
        """

        if arcs is None:
            arcs = []

            for x in self.crossword.variables:
                for y in self.crossword.neighbors(x):
                    arcs.append((x, y))

        else:
            arcs = list(arcs)

        while arcs:

            x, y = arcs.pop(0)

            if self.revise(x, y):

                if len(self.domains[x]) == 0:
                    return False

                for z in self.crossword.neighbors(x):

                    if z != y:
                        arcs.append((z, x))

        return True

    def assignment_complete(self, assignment):
        """
        Return True if assignment is complete.
        """

        return set(assignment.keys()) == set(self.crossword.variables)

    def consistent(self, assignment):
        """
        Return True if assignment is consistent.
        """

        # Check that every word has correct length
        for variable, word in assignment.items():

            if len(word) != variable.length:
                return False

        # Check that all assigned words are different
        words = list(assignment.values())

        if len(words) != len(set(words)):
            return False

        # Check overlaps
        for variable, word in assignment.items():

            for neighbor in self.crossword.neighbors(variable):

                if neighbor in assignment:

                    overlap = self.crossword.overlaps[
                        variable, neighbor
                    ]

                    if overlap is not None:

                        i, j = overlap

                        if word[i] != assignment[neighbor][j]:
                            return False

        return True

    def order_domain_values(self, var, assignment):
        """
        Return values from var's domain ordered by the
        least-constraining-value heuristic.
        """

        values = []

        for value in self.domains[var]:

            ruled_out = 0

            for neighbor in self.crossword.neighbors(var):

                if neighbor in assignment:
                    continue

                overlap = self.crossword.overlaps[
                    var, neighbor
                ]

                if overlap is None:
                    continue

                i, j = overlap

                for neighbor_value in self.domains[neighbor]:

                    if value[i] != neighbor_value[j]:
                        ruled_out += 1

            values.append((ruled_out, value))

        values.sort()

        return [value for _, value in values]

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable using:
        1. Minimum Remaining Values
        2. Degree heuristic as tie-breaker
        """

        unassigned = [
            var
            for var in self.crossword.variables
            if var not in assignment
        ]

        return min(
            unassigned,
            key=lambda var: (
                len(self.domains[var]),
                -len(self.crossword.neighbors(var))
            )
        )

    def backtrack(self, assignment):
        """
        Return a completed assignment using backtracking search.
        Return None if no solution exists.
        """

        if self.assignment_complete(assignment):
            return assignment

        var = self.select_unassigned_variable(assignment)

        for value in self.order_domain_values(var, assignment):

            assignment[var] = value

            if self.consistent(assignment):

                saved_domains = {
                    variable: self.domains[variable].copy()
                    for variable in self.domains
                }

                self.domains[var] = {value}

                if self.ac3():

                    result = self.backtrack(assignment)

                    if result is not None:
                        return result

                self.domains = saved_domains

            del assignment[var]

        return None

    def solve(self):
        """
        Enforce node consistency, enforce arc consistency,
        and then solve the CSP using backtracking.
        """

        self.enforce_node_consistency()

        if not self.ac3():
            return None

        return self.backtrack({})


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]

    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)

    # Solve crossword
    assignment = creator.solve()

    if assignment is None:
        print("No solution.")

    else:
        creator.print(assignment)

        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
