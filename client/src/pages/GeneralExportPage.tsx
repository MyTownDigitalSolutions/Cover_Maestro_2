import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  FormControl,
  Grid,
  InputLabel,
  ListItemText,
  MenuItem,
  OutlinedInput,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'
import type { Manufacturer, Model, Series } from '../types'
import { exportApi, manufacturersApi, modelsApi, seriesApi } from '../services/api'

type MarketplaceKey = 'amazon' | 'ebay' | 'etsy' | 'reverb'

const MARKETPLACE_OPTIONS: { key: MarketplaceKey; label: string }[] = [
  { key: 'amazon', label: 'Amazon' },
  { key: 'ebay', label: 'eBay' },
  { key: 'etsy', label: 'Etsy' },
  { key: 'reverb', label: 'Reverb' },
]

export default function GeneralExportPage() {
  const [loading, setLoading] = useState(true)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [manufacturers, setManufacturers] = useState<Manufacturer[]>([])
  const [allSeries, setAllSeries] = useState<Series[]>([])
  const [allModels, setAllModels] = useState<Model[]>([])

  const [selectedManufacturer, setSelectedManufacturer] = useState<number | ''>('')
  const [selectedSeriesIds, setSelectedSeriesIds] = useState<number[]>([])
  const [selectedModels, setSelectedModels] = useState<Set<number>>(new Set())
  const [selectedMarketplaces, setSelectedMarketplaces] = useState<Record<MarketplaceKey, boolean>>({
    amazon: false,
    ebay: false,
    etsy: false,
    reverb: false,
  })

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        setError(null)
        const [mfrs, seriesRows, modelRows] = await Promise.all([
          manufacturersApi.list(),
          seriesApi.list(),
          modelsApi.list(),
        ])
        setManufacturers(mfrs)
        setAllSeries(seriesRows)
        setAllModels(modelRows)
      } catch (err: any) {
        console.error(err)
        setError(err?.message || 'Failed to load export data.')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  const sortedManufacturers = useMemo(() => {
    return [...manufacturers].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }))
  }, [manufacturers])

  const filteredSeries = useMemo(() => {
    if (!selectedManufacturer) return []
    return allSeries
      .filter((s) => s.manufacturer_id === selectedManufacturer)
      .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }))
  }, [allSeries, selectedManufacturer])

  const filteredModels = useMemo(() => {
    if (!selectedManufacturer) return []
    const allowedSeriesIds = new Set(
      allSeries.filter((s) => s.manufacturer_id === selectedManufacturer).map((s) => s.id),
    )
    let rows = allModels.filter((m) => allowedSeriesIds.has(m.series_id))
    if (selectedSeriesIds.length > 0) {
      const selectedSet = new Set(selectedSeriesIds)
      rows = rows.filter((m) => selectedSet.has(m.series_id))
    }
    return rows.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }))
  }, [allModels, allSeries, selectedManufacturer, selectedSeriesIds])

  useEffect(() => {
    const visibleIds = new Set(filteredModels.map((m) => m.id))
    setSelectedModels((prev) => new Set([...prev].filter((id) => visibleIds.has(id))))
  }, [filteredModels])

  const selectedMarketplaceKeys = useMemo(() => {
    return Object.entries(selectedMarketplaces)
      .filter(([, isSelected]) => isSelected)
      .map(([key]) => key as MarketplaceKey)
  }, [selectedMarketplaces])

  const allVisibleSelected = filteredModels.length > 0 && filteredModels.every((m) => selectedModels.has(m.id))
  const someVisibleSelected = filteredModels.some((m) => selectedModels.has(m.id))

  const handleDownload = async () => {
    if (selectedModels.size === 0 || selectedMarketplaceKeys.length === 0) return
    setDownloading(true)
    setError(null)
    try {
      const response = await exportApi.downloadGeneralZip(
        Array.from(selectedModels),
        selectedMarketplaceKeys,
        'individual',
      )

      const contentDisposition = String(response.headers?.['content-disposition'] || '')
      const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
      const plainMatch = contentDisposition.match(/filename=\"?([^\";]+)\"?/i)
      let filename = `General_Export_${new Date().toISOString().slice(0, 10)}.zip`
      if (utf8Match?.[1]) {
        filename = decodeURIComponent(utf8Match[1])
      } else if (plainMatch?.[1]) {
        filename = plainMatch[1]
      }

      const blob = new Blob([response.data], { type: 'application/zip' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.parentNode?.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (err: any) {
      console.error(err)
      let message = 'Failed to download batch export ZIP.'
      try {
        const blob = err?.response?.data
        if (blob instanceof Blob) {
          const text = await blob.text()
          if (text) {
            const parsed = JSON.parse(text)
            const detail = parsed?.detail
            if (typeof detail === 'string') {
              message = detail
            } else if (detail) {
              message = JSON.stringify(detail)
            }
          }
        }
      } catch {
        // no-op
      }
      setError(message)
    } finally {
      setDownloading(false)
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', pt: 6 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        General Export
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
        Select models and marketplaces, then download one ZIP bundle.
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>Filter Models</Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Manufacturer</InputLabel>
              <Select
                value={selectedManufacturer}
                label="Manufacturer"
                onChange={(e) => {
                  const value = e.target.value
                  setSelectedManufacturer(value === '' ? '' : Number(value))
                  setSelectedSeriesIds([])
                  setSelectedModels(new Set())
                }}
              >
                <MenuItem value=""><em>Select manufacturer</em></MenuItem>
                {sortedManufacturers.map((m) => (
                  <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth disabled={!selectedManufacturer}>
              <InputLabel>Series</InputLabel>
              <Select
                multiple
                value={selectedSeriesIds}
                label="Series"
                input={<OutlinedInput label="Series" />}
                renderValue={(selected) => {
                  const ids = selected as number[]
                  if (ids.length === 0) return 'All series'
                  const names = filteredSeries.filter((s) => ids.includes(s.id)).map((s) => s.name)
                  return names.join(', ')
                }}
                onChange={(e) => {
                  const value = e.target.value
                  const next = typeof value === 'string'
                    ? value.split(',').map((v) => Number(v))
                    : (value as number[])
                  setSelectedSeriesIds(next)
                }}
              >
                {filteredSeries.map((s) => (
                  <MenuItem key={s.id} value={s.id}>
                    <Checkbox checked={selectedSeriesIds.includes(s.id)} />
                    <ListItemText primary={s.name} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>Marketplaces</Typography>
        <Stack direction="row" spacing={3} flexWrap="wrap">
          {MARKETPLACE_OPTIONS.map((option) => (
            <Box key={option.key} sx={{ display: 'flex', alignItems: 'center' }}>
              <Checkbox
                checked={selectedMarketplaces[option.key]}
                onChange={(e) =>
                  setSelectedMarketplaces((prev) => ({ ...prev, [option.key]: e.target.checked }))
                }
              />
              <Typography>{option.label}</Typography>
            </Box>
          ))}
        </Stack>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
          <Typography variant="h6">Models to Export</Typography>
          <Typography color="text.secondary">
            Showing {filteredModels.length} models • {selectedModels.size} selected
          </Typography>
        </Stack>

        {!selectedManufacturer ? (
          <Alert severity="info">Select a manufacturer to view models.</Alert>
        ) : filteredModels.length === 0 ? (
          <Alert severity="info">No models found for the current filter.</Alert>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={!allVisibleSelected && someVisibleSelected}
                    checked={allVisibleSelected}
                    onChange={(e) => {
                      const checked = e.target.checked
                      setSelectedModels((prev) => {
                        const next = new Set(prev)
                        if (checked) {
                          filteredModels.forEach((m) => next.add(m.id))
                        } else {
                          filteredModels.forEach((m) => next.delete(m.id))
                        }
                        return next
                      })
                    }}
                  />
                </TableCell>
                <TableCell>Model</TableCell>
                <TableCell>Series</TableCell>
                <TableCell>Manufacturer</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredModels.map((model) => {
                const series = allSeries.find((s) => s.id === model.series_id)
                const manufacturer = manufacturers.find((m) => m.id === series?.manufacturer_id)
                return (
                  <TableRow key={model.id} hover selected={selectedModels.has(model.id)}>
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={selectedModels.has(model.id)}
                        onChange={(e) => {
                          const checked = e.target.checked
                          setSelectedModels((prev) => {
                            const next = new Set(prev)
                            if (checked) next.add(model.id)
                            else next.delete(model.id)
                            return next
                          })
                        }}
                      />
                    </TableCell>
                    <TableCell>{model.name}</TableCell>
                    <TableCell>{series?.name || '—'}</TableCell>
                    <TableCell>{manufacturer?.name || '—'}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}
      </Paper>

      <Button
        variant="contained"
        color="primary"
        startIcon={downloading ? <CircularProgress size={18} color="inherit" /> : <DownloadIcon />}
        onClick={handleDownload}
        disabled={downloading || selectedModels.size === 0 || selectedMarketplaceKeys.length === 0}
      >
        {downloading ? 'EXPORTING...' : 'DOWNLOAD BATCH ZIP'}
      </Button>
    </Box>
  )
}
