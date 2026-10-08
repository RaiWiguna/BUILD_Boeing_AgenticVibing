import type { LayoutView } from '../../../types';

/**
 * Fictional aerodrome layout (FICTIONAL_LOCAL_XY, metres). Extends the geometry idea of
 * tests/fixtures/layouts/fictional-runway.json for display. Not an operational chart.
 */
export const FICTIONAL_LAYOUT: LayoutView = {
  version: 'fictional-2',
  units: 'm',
  caption: 'Fictional layout · metres · not an operational chart',
  runways: [
    {
      id: '09/27',
      ends: ['09', '27'],
      polygon: [
        [-1400, -23],
        [1400, -23],
        [1400, 23],
        [-1400, 23],
      ],
      centerline: [
        [-1400, 0],
        [1400, 0],
      ],
    },
  ],
  hold_lines: [
    { id: 'HL-A27', label: 'Hold line RWY 27', runway: '09/27', points: [[1112, -78], [1188, -78]] },
    { id: 'HL-B', label: 'Hold line B', runway: '09/27', points: [[-338, 78], [-262, 78]] },
  ],
  taxiways: [
    {
      id: 'TWY-A',
      label: 'TWY A',
      path: [
        [-1250, -300],
        [-300, -300],
        [700, -300],
        [1030, -250],
        [1150, -150],
        [1150, -23],
      ],
      label_at: [-420, -300],
    },
    {
      id: 'TWY-B',
      label: 'TWY B',
      path: [
        [-300, 23],
        [-300, 150],
        [-480, 300],
        [-1250, 300],
      ],
      label_at: [-820, 300],
    },
  ],
  bounds: { min_x: -1460, max_x: 1460, min_y: -380, max_y: 380 },
};
