SELECT DISTINCT chart_date FROM music.fact_chart
WHERE chart_type = 'weekly_top_songs' AND country = 'global'
ORDER BY chart_date DESC;
