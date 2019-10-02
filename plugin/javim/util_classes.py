import uuid
from time import sleep
from threading import Thread

class OffsetChainUpdate:

    def perform_update(self, chain):
        pass

class ReplaceOffsetChainUpdate(OffsetChainUpdate):

    def __init__(self, mod_map):
        self.mod_map = mod_map

    def perform_update(self, chain):
        min_index = None
        for index, length in self.mod_map.items():
            chain.elements[index].length = length
            if min_index is None or index < min_index:
                min_index = index
        return min_index


class DeleteOffsetChainUpdate(OffsetChainUpdate):

    def __init__(self, del_indexes):
        self.del_indexes = del_indexes

    def perform_update(self, chain):
        min_index = None
        for index in self.del_indexes:
            chain.remove(index, False)
            if min_index is None or index < min_index:
                min_index = index
        return min_index

class ReplaceRangeOffsetChainUpdate(OffsetChainUpdate):

    def __init__(self, start, end, lengths):
        self.start = start
        self.end = end
        self.lengths = lengths

    def perform_update(self, chain):
        first = chain.elements[self.start]
        last = chain.elements[self.end - 1]

        for index in range(self.end, self.start, -1):
            del chain.elements[index - 1]

        prev_elem = first.prev_elem
        index = self.start
        for length in self.lengths:
            elem = OffsetChainElement(chain, length, prev_elem)
            if prev_elem:
                prev_elem.next_elem = elem
            chain.elements.insert(index, elem)
            index += 1
            prev_elem = elem

        if last.next_elem:
            prev_elem.next_elem = last.next_elem
            last.next_elem.prev_elem = prev_elem

        return self.start


class OffsetChain:

    def __init__(self):
        self.elements = []
        self.invalid_index = -1

    def invalidate(self, index):
        self.invalid_index = index if index < self.invalid_index else self.invalid_index

    def update(self, element):
        elem = element
        while elem is not None:
            if elem.prev_elem:
                elem.offset = elem.prev_elem.offset + elem.prev_elem.length
            else:
                elem.offset = 0

            elem = elem.next_elem

    def mass_update(self, update: OffsetChainUpdate):
        index = update.perform_update(self)
        self.update(self.elements[index])

    def append(self, length):
        elem = OffsetChainElement(self, length)
        if self.elements:
            prev = self.elements[-1]
            prev.next_elem = elem
            elem.prev_elem = prev

        self.update(elem)
        self.elements.append(elem)

    def insert(self, index, length, update=True):
        if index >= len(self.elements):
            self.append(length)
        else:
            next_elem = self.elements[index]
            elem = OffsetChainElement(self, length, next_elem.prev_elem, next_elem)
            if next_elem.prev_elem:
                next_elem.prev_elem.next_elem = elem
            next_elem.prev_elem = elem
            if update: self.update(elem)

    def remove(self, index, update=True):
        elem = self.elements[index]
        if elem.prev_elem:
            elem.prev_elem.next_elem = elem.next_elem
            if elem.next_elem:
                elem.next_elem.prev_elem = elem.prev_elem
                if update: self.update(elem.next_elem)
        elif elem.next_elem:
            elem.next_elem.prev_elem = None
            if update: self.update(elem.next_elem)

        del self.elements[index]

    def __len__(self):
        return len(self.elements)



class OffsetChainElement:

    def __init__(self, chain, length, prev_elem=None, next_elem=None):
        self.chain = chain
        self.length = length
        self.prev_elem = prev_elem
        self.next_elem = next_elem
        self.offset = 0

class Switch:

    def __init__(self, on=False):
        self.on = on

    def toggle(self):
        self.on = not self.on

    def set_on(self):
        self.on = True

    def set_off(self):
        self.on = False

    def is_on(self):
        return self.on


class DelayedAction:

    def __init__(self, delay, action):
        self.delay = delay
        self.action = action
        self.active = False
        self.switch = Switch(False)
        self.thread = None

    def reset(self):
        self.switch.set_off()
        self.switch = Switch(True)
        self.thread = Thread(target=self.__run__, args=(self.switch,))
        self.thread.start()

    def __run__(self, switch):
        sleep(self.delay)
        if switch.on: self.action()





