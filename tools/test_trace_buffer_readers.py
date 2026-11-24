import unittest

from trace_buffer_readers import compare, inputs


class TraceReaders(unittest.TestCase):
    shader = '0123456789abcdef'

    @staticmethod
    def event(tag, op, frame, submission):
        return f'2026-01-01T00:00:00Z INFO host: {tag}: {op} frame={frame} submission={submission}\n'

    def test_later_submission_and_half_open_overlap(self):
        w = f'dispatch 1x1x1 [compute {self.shader}] [heap 1: Placed(true, [1], [2], title 0x100+0x20 host Some(\n 0xbeef,\n)]'
        reader = lambda start: f'dispatch 1x1x1 {self.shader} Srv s0+8: buffer Some(({start}, 8))'
        log = ''.join([self.event('wait neighbor', w, 10, 5), self.event('writer event', reader(256), 10, 5),
                       self.event('writer event', reader(288), 10, 6), self.event('writer event', reader(256), 11, 7),
                       self.event('writer event', reader(284), 10, 8)])
        self.assertEqual(compare(log, 10, self.shader), [(5, 256, 32, (8, f'{self.shader} Srv s0+8', 4))])

    def test_resource_extent_is_not_effective_view(self):
        op = f'{self.shader} Srv s0+24: placed uav=false dim 1 32x1 f0 layout 0x1 at 0x100'
        self.assertEqual(list(inputs(op)), [(256, 32, f'{self.shader} Srv s0+24 (enclosing buffer)')])

    def test_unrelated_heap_slot_does_not_inherit_next_address(self):
        op = '[heap 1: Shader(5,None)] [heap 2: Placed(true, [1], [2], title 0x200+0x20 host Some(0x300))]'
        self.assertEqual(list(inputs(op)), [])


if __name__ == '__main__':
    unittest.main()
