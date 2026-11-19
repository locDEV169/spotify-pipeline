import assert from 'node:assert/strict'
import { demoTracks, filterTracks, summarize, tracksForWeek, weeks } from '../src/lib/demo-data.ts'

assert.equal(summarize(demoTracks).coverage, 75)
assert.equal(summarize(demoTracks).newEntries, 2)
assert.equal(filterTracks(demoTracks, '  WEEKND ', false).length, 2)
assert.equal(filterTracks(demoTracks, '', true).length, 2)
assert.equal(filterTracks(demoTracks, 'M83', true).length, 0)
assert.equal(summarize([]).coverage, 0)
assert.equal(summarize(filterTracks(demoTracks, '', true)).energy, 0)
assert.notEqual(tracksForWeek(weeks[0])[0].id, tracksForWeek(weeks[1])[0].id)
assert.equal(demoTracks[0].rank, 1)
console.log('PASS: filtering, missing features, coverage, empty data and weekly fixtures.')
