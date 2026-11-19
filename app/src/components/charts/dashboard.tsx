import { useState } from 'react'
import { Activity, ArrowDown, ArrowUp, BarChart3, Check, Database, Download, Globe2, Layers3, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { filterTracks, summarize, tracksForWeek, weeks } from '@/lib/demo-data'

export function Dashboard() {
  const [week, setWeek] = useState<string>(weeks[0])
  const [query, setQuery] = useState('')
  const [missingOnly, setMissingOnly] = useState(false)
  const tracks = tracksForWeek(week)
  const rows = filterTracks(tracks, query, missingOnly)
  const summary = summarize(tracks)

  function exportCsv() {
    const fields = ['rank', 'name', 'artist', 'previousRank', 'energy', 'danceability', 'valence', 'tempo'] as const
    const csv = [fields.join(','), ...rows.map(row => fields.map(field => {
      const value = row[field]
      return value === null ? '' : `"${String(value).replaceAll('"', '""')}"`
    }).join(','))].join('\r\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `demo-global-chart-${week}.csv`
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return (
    <div className="min-h-screen bg-[#f5f7f9] text-slate-900 lg:grid lg:grid-cols-[228px_1fr]">
      <aside className="flex flex-col border-b border-slate-200 bg-white lg:sticky lg:top-0 lg:h-screen lg:border-r lg:border-b-0">
        <div className="flex items-center gap-3 px-6 py-7"><div className="flex size-9 items-center justify-center rounded-xl bg-emerald-600 text-white"><BarChart3 size={21} /></div><span className="text-lg font-bold tracking-tight">Chartroom<span className="text-emerald-600">.</span></span></div>
        <div className="px-4 pb-5 lg:pt-5"><p className="mb-3 px-3 text-xs font-semibold tracking-widest text-slate-400">WORKSPACE</p><a href="#overview" className="flex items-center gap-3 rounded-lg bg-emerald-50 px-3 py-3 text-sm font-semibold text-emerald-800"><Activity size={18} />Overview</a><a href="#rankings" className="mt-1 flex items-center gap-3 rounded-lg px-3 py-3 text-sm text-slate-600 hover:bg-slate-50"><BarChart3 size={18} />Chart rankings</a><a href="#quality" className="mt-1 flex items-center gap-3 rounded-lg px-3 py-3 text-sm text-slate-600 hover:bg-slate-50"><Layers3 size={18} />Data quality</a></div>
        <div className="mx-5 mb-5 hidden rounded-xl border border-slate-200 p-4 lg:mt-auto lg:block"><Database size={18} className="mb-3 text-slate-400" /><p className="text-sm font-semibold">Your data workspace</p><p className="mt-2 text-sm leading-6 text-slate-500">Charts, metadata and audio features. All in one view.</p><div className="mt-4 border-t border-slate-100 pt-3 text-xs font-medium text-amber-700">Demo · Database not connected</div></div>
        <div className="hidden border-t border-slate-100 px-6 py-5 text-xs text-slate-400 lg:block">Spotify Pipeline / v0.1</div>
      </aside>

      <div className="min-w-0">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-6 py-4 xl:px-10"><p className="text-sm text-slate-400">Workspace <span className="mx-2">/</span> <span className="font-medium text-slate-700">Overview</span></p><div className="flex items-center gap-3"><span className="rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800">SAMPLE DATA</span><span className="text-sm text-slate-500">Weekly snapshot</span></div></header>
        <main id="overview" className="mx-auto max-w-[1600px] space-y-7 px-5 py-8 sm:px-7 xl:px-10">
          <div className="flex flex-wrap items-end justify-between gap-5"><div><p className="mb-2 text-xs font-semibold tracking-[0.16em] text-emerald-700">MUSIC INTELLIGENCE</p><h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Charts overview</h1><p className="mt-3 text-sm leading-6 text-slate-500">Understand what is trending, and the data behind it.</p></div><Button onClick={exportCsv} variant="outline" className="h-10 rounded-lg bg-white px-4"><Download size={16} />Export CSV</Button></div>

          <div className="flex flex-wrap items-center gap-3"><div className="flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm"><Globe2 size={16} className="text-slate-400" />Global</div><Select value={week} onValueChange={value => { if (value) setWeek(value) }}><SelectTrigger aria-label="Chart week" className="h-10! min-w-48 bg-white"><SelectValue>{`Week of ${week}`}</SelectValue></SelectTrigger><SelectContent>{weeks.map(value => <SelectItem key={value} value={value}>Week of {value}</SelectItem>)}</SelectContent></Select><span className="text-sm text-slate-400">Weekly Top Songs</span></div>

          <section aria-label="Chart summary" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[
            { label: 'Chart entries', value: summary.total, note: 'Tracks in this sample', color: 'text-slate-500' },
            { label: 'Feature coverage', value: `${summary.coverage.toFixed(0)}%`, note: `${summary.matched} of ${summary.total} tracks matched`, color: 'text-emerald-700' },
            { label: 'Average energy', value: summary.energy.toFixed(2), note: 'Matched tracks only · 0–1', color: 'text-slate-500' },
            { label: 'New entries', value: summary.newEntries, note: 'No previous rank in sample', color: 'text-slate-500' },
          ].map(stat => <article key={stat.label} className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">{stat.label}</p><p className="mt-3 text-3xl font-semibold tracking-tight tabular-nums">{stat.value}</p><p className={`mt-3 text-xs ${stat.color}`}>{stat.note}</p></article>)}</section>

          <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
            <section className="rounded-xl border border-slate-200 bg-white p-6"><div className="flex items-start justify-between"><div><h2 className="font-semibold">The sound of this chart</h2><p className="mt-1 text-sm text-slate-500">Average audio features across matched tracks</p></div><span className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-500">ReccoBeats</span></div><div className="mt-7 space-y-5">{[['Danceability', summary.danceability, 'bg-emerald-500'], ['Energy', summary.energy, 'bg-teal-500'], ['Valence', summary.valence, 'bg-sky-400']].map(([label, value, color]) => <div key={String(label)} className="grid grid-cols-[100px_1fr_40px] items-center gap-4 text-sm"><span className="text-slate-600">{label}</span><div role="meter" aria-label={String(label)} aria-valuenow={Number(value)} aria-valuemin={0} aria-valuemax={1} className="h-3 rounded-full bg-slate-100"><div className={`h-full rounded-full ${color}`} style={{ width: `${Number(value) * 100}%` }} /></div><span className="text-right font-medium tabular-nums">{Number(value).toFixed(2)}</span></div>)}</div><p className="mt-7 text-xs text-slate-400">Scale 0–1. Valence describes musical positivity. Missing features are excluded.</p></section>
            <section id="quality" className="rounded-xl border border-slate-200 bg-white p-6"><h2 className="font-semibold">Feature availability</h2><p className="mt-1 text-sm text-slate-500">Missing data stays visible in your chart.</p><div className="mt-6 flex items-center gap-7"><div role="img" aria-label={`${summary.coverage}% feature coverage`} className="flex size-28 shrink-0 items-center justify-center rounded-full" style={{ background: `conic-gradient(#10b981 ${summary.coverage}%, #e2e8f0 0)` }}><div className="flex size-22 flex-col items-center justify-center rounded-full bg-white"><span className="text-2xl font-semibold">{summary.coverage.toFixed(0)}%</span><span className="text-xs text-slate-400">coverage</span></div></div><div className="space-y-3 text-sm"><p className="flex items-center gap-2"><span className="size-2 rounded-full bg-emerald-500" />Matched <strong className="ml-3">{summary.matched}</strong></p><p className="flex items-center gap-2"><span className="size-2 rounded-full bg-slate-300" />Missing <strong className="ml-3">{summary.total - summary.matched}</strong></p><button onClick={() => { setMissingOnly(true); document.getElementById('rankings')?.scrollIntoView({ behavior: 'smooth' }) }} className="rounded text-xs font-medium text-emerald-700 underline underline-offset-4 focus-visible:outline-2">View missing tracks</button></div></div></section>
          </div>

          <section id="rankings" className="overflow-hidden rounded-xl border border-slate-200 bg-white"><div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 p-5"><div className="flex items-center gap-3"><h2 className="font-semibold">Chart rankings</h2><span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{summary.total} tracks</span></div><div className="flex flex-wrap items-center gap-3"><label className="flex h-9 items-center gap-2 rounded-lg border border-slate-200 px-3"><Search size={15} className="text-slate-400" /><input aria-label="Search tracks or artists" placeholder="Search tracks or artists…" value={query} onChange={event => setQuery(event.target.value)} className="w-40 bg-transparent text-sm outline-none sm:w-48" /></label><label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600"><input type="checkbox" checked={missingOnly} onChange={event => setMissingOnly(event.target.checked)} className="size-4 accent-emerald-600" />Missing only</label></div></div>
            <div className="overflow-x-auto"><table className="w-full min-w-[750px] text-left text-sm"><caption className="sr-only">Synthetic Global weekly chart for {week}</caption><thead className="bg-slate-50/70 text-xs text-slate-500"><tr>{['Rank', 'Track / Artist', 'Change', 'Energy', 'Danceability', 'Features'].map(label => <th key={label} scope="col" className="px-5 py-3.5 font-medium">{label}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{rows.map(track => { const delta = track.previousRank === null ? null : track.previousRank - track.rank; return <tr key={track.id} className="hover:bg-slate-50/80"><td className="px-5 py-4 font-medium tabular-nums text-slate-500">{String(track.rank).padStart(2, '0')}</td><td className="px-5 py-4"><p className="font-medium">{track.name}</p><p className="mt-1 text-xs text-slate-500">{track.artist}</p></td><td className="px-5 py-4">{delta === null ? <span className="rounded bg-sky-50 px-2 py-1 text-xs font-semibold text-sky-700">NEW</span> : <span className={`flex items-center gap-1 text-xs font-medium ${delta > 0 ? 'text-emerald-700' : delta < 0 ? 'text-rose-600' : 'text-slate-400'}`}>{delta > 0 ? <ArrowUp size={14} aria-label="Up" /> : delta < 0 ? <ArrowDown size={14} aria-label="Down" /> : '—'}{delta !== 0 && Math.abs(delta)}</span>}</td><td className="px-5 py-4 tabular-nums text-slate-600">{track.energy?.toFixed(2) ?? '—'}</td><td className="px-5 py-4 tabular-nums text-slate-600">{track.danceability?.toFixed(2) ?? '—'}</td><td className="px-5 py-4">{track.energy !== null ? <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700"><Check size={12} />Available</span> : <span className="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800">Missing</span>}</td></tr> })}</tbody></table>{rows.length === 0 && <p role="status" className="p-10 text-center text-sm text-slate-500">No tracks match your filters.</p>}</div><div aria-live="polite" className="flex flex-wrap justify-between gap-2 border-t border-slate-100 px-5 py-4 text-xs text-slate-500"><span>Showing {rows.length} of {summary.total} tracks</span><span>Chart source: Spotify Charts · Features: ReccoBeats</span></div></section>
          <footer className="flex flex-wrap justify-between gap-2 pb-3 text-xs leading-6 text-slate-400"><span>Spotify Pipeline · Analytics workspace</span><span>Demo fixtures only. Rankings and metrics are illustrative, not live data.</span></footer>
        </main>
      </div>
    </div>
  )
}
