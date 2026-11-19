export type Track = {
  id: string
  name: string
  artist: string
  rank: number
  previousRank: number | null
  energy: number | null
  danceability: number | null
  valence: number | null
  tempo: number | null
}

// Synthetic fixtures for the UI demo; these are not live Spotify rankings.
export const weeks = ['2026-11-12', '2026-11-05'] as const
export const demoTracks: Track[] = [
  { id: 'demo-1', name: 'Midnight City', artist: 'M83', rank: 1, previousRank: 3, energy: 0.81, danceability: 0.65, valence: 0.52, tempo: 105 },
  { id: 'demo-2', name: 'Birds of a Feather', artist: 'Billie Eilish', rank: 2, previousRank: 1, energy: 0.51, danceability: 0.75, valence: 0.44, tempo: 105 },
  { id: 'demo-3', name: 'After Hours', artist: 'The Weeknd', rank: 3, previousRank: 6, energy: 0.57, danceability: 0.64, valence: 0.14, tempo: 109 },
  { id: 'demo-4', name: 'Golden Hour', artist: 'JVKE', rank: 4, previousRank: null, energy: null, danceability: null, valence: null, tempo: null },
  { id: 'demo-5', name: 'Levitating', artist: 'Dua Lipa', rank: 5, previousRank: 4, energy: 0.83, danceability: 0.7, valence: 0.91, tempo: 103 },
  { id: 'demo-6', name: 'Heat Waves', artist: 'Glass Animals', rank: 6, previousRank: 8, energy: 0.53, danceability: 0.76, valence: 0.53, tempo: 81 },
  { id: 'demo-7', name: 'Saturn', artist: 'SZA', rank: 7, previousRank: null, energy: null, danceability: null, valence: null, tempo: null },
  { id: 'demo-8', name: 'Blinding Lights', artist: 'The Weeknd', rank: 8, previousRank: 5, energy: 0.73, danceability: 0.51, valence: 0.33, tempo: 171 },
]

export function tracksForWeek(week: string): Track[] {
  if (week === weeks[0]) return demoTracks
  return [...demoTracks].reverse().map((track, index) => ({
    ...track, rank: index + 1, previousRank: index === 0 ? null : Math.max(1, index),
  }))
}

export function filterTracks(tracks: Track[], query: string, missingOnly: boolean) {
  const search = query.trim().toLowerCase()
  return tracks.filter(track =>
    `${track.name} ${track.artist}`.toLowerCase().includes(search) &&
    (!missingOnly || track.energy === null),
  )
}

export function summarize(tracks: Track[]) {
  const matched = tracks.filter(track => track.energy !== null)
  const average = (key: 'energy' | 'danceability' | 'valence') => matched.length
    ? matched.reduce((sum, track) => sum + (track[key] ?? 0), 0) / matched.length : 0
  return {
    total: tracks.length,
    matched: matched.length,
    coverage: tracks.length ? matched.length / tracks.length * 100 : 0,
    newEntries: tracks.filter(track => track.previousRank === null).length,
    energy: average('energy'), danceability: average('danceability'), valence: average('valence'),
  }
}
