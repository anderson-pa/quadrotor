from ctypes import *
from collections import namedtuple

# define return structures for DLL function calls
six_names = 'fx fy fz mx my mz'
six_array = namedtuple('SixArray', six_names)
field_six_array = [(name, c_short) for name in six_names.split()]

force_names = 'fx fy fz mx my mz v1 v2'
force_array = namedtuple('ForceArray', force_names)
field_force_array = [(name, c_short) for name in force_names.split()]


class ForceArray(Structure):
    _fields_ = field_force_array


class ClockedForceArray(Structure):
    _fields_ = [('clk', c_ushort)] + field_force_array


# load the DLL and apply return types as appropriate
jr3 = cdll.LoadLibrary('./jr3/jr3.dll')
jr3.GetForceArray.restype = ForceArray
jr3.GetClockedForceArray.restype = ClockedForceArray


class Jr3:
    def __init__(self, device_index=1, channel=0):
        self._handle = jr3.GetHandle(device_index)
        self._channel = channel

    def _read_word(self, offset):
        return jr3.ReadWord(self._handle, self._channel, offset)

    def _read_words(self, offset, length) -> list:
        words_def = c_short * length
        words = words_def()
        jr3.ReadWords(self._handle, self._channel, offset, length, words)
        return list(words)

    def _read_word_list(self, offsets):
        return [self._read_word(offset) for offset in offsets]

    @property
    def copyright(self):
        copyright = self._read_words(0x40, 18)
        return ''.join([c.to_bytes(2, 'big').decode('utf-8') for c in copyright])

    @property
    def serial_num(self):
        return self._read_word(0xf8)

    @property
    def offsets(self):
        return six_array(*self._read_words(0x88, 6))

    @property
    def fs_min(self):
        return six_array(*self._read_words(0x70, 6))

    @property
    def fs_max(self):
        return six_array(*self._read_words(0x78, 6))

    @property
    def fs(self):
        return force_array(*self._read_words(0x80, 8))

    def read_forces(self, filter=0, scaled=True):
        if filter < 0 or filter > 6:
            raise ValueError('filter must be 0-6 inclusive.')
        fa = jr3.GetForceArray(self._handle, self._channel, filter)
        fa = [getattr(fa, f[0]) for f in fa._fields_]

        if scaled:
            fa = [f / 2**14 * fs for f, fs, in zip(fa, self.fs)]

        return force_array(*fa)

    def read_clocked_forces(self, filter=1, scaled=True):
        if filter < 1 or filter > 6:
            raise ValueError('filter must be 1-6 inclusive.')
        cfa = jr3.GetClockedForceArray(self._handle, self._channel, filter)
        cfa = [getattr(cfa, f[0]) for f in cfa._fields_]
        clk, *cfa = cfa

        if scaled:
            cfa = [f / 2**14 * fs for f, fs, in zip(cfa, self.fs)]

        return clk, force_array(*cfa)

    @property
    def counters(self):
        return [c_ushort(cnt).value for cnt in self._read_words(0xe8, 6)]

#  shunts 		0x60, 6
#  def fs 		0x68, 6
#  load env # 	0x6f
#  min fs		0x70, 6
#  xForm#		0x77
#  max fs		0x78, 6
#  fs			0x80, 8
##  ofs			0x88, 6
#  ofs#			0x8e
#  vect axes	0x8f

#  f0			0x90, 8
#  f1			0x98, 8
#  f2			0xa0, 8
#  f3			0xa8, 8
#  f4			0xb0, 8
#  f5			0xb8, 8
#  f6			0xc0, 8

#  rate			0xc8, 8
#  min			0xd0, 8
#  max			0xd8, 8
