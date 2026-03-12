import { useEffect, useState, useMemo } from 'react'
import {
    Box, Typography, Paper, Button, Grid, FormControl, InputLabel, Select, MenuItem, CircularProgress, Alert, Chip,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Checkbox
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import { manufacturersApi, seriesApi, modelsApi, pricingApi } from '../services/api'
import type { Manufacturer, Series, Model } from '../types'

// Sentinel value for "All Series"
const ALL_SERIES_VALUE = '__ALL_SERIES__'
// Sentinel value for "Multi Series" mode (internal state usage)
const MULTI_SERIES_VALUE = '__MULTI__'

export default function EtsyExportPage() {
    const [manufacturers, setManufacturers] = useState<Manufacturer[]>([])
    const [allSeries, setAllSeries] = useState<Series[]>([])
    const [allModels, setAllModels] = useState<Model[]>([])

    const [selectedManufacturer, setSelectedManufacturer] = useState<number | ''>('')
    // selectedSeries (single) is deprecated for filtering, using multi-select ids instead
    const [selectedSeriesValue, setSelectedSeriesValue] = useState<string>('')
    const [selectedSeriesIds, setSelectedSeriesIds] = useState<number[]>([])
    const [selectedModels, setSelectedModels] = useState<Set<number>>(new Set())

    const [loading, setLoading] = useState(true)
    const [recalculating, setRecalculating] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Load initial data
    useEffect(() => {
        loadData()
    }, [])

    const loadData = async () => {
        try {
            setLoading(true)
            const [mfrs, series, models] = await Promise.all([
                manufacturersApi.list(),
                seriesApi.list(),
                modelsApi.list()
            ])
            setManufacturers(mfrs)
            setAllSeries(series)
            setAllModels(models)
        } catch (err: any) {
            setError(err.message || 'Failed to load data')
        } finally {
            setLoading(false)
        }
    }

    // Sorted Manufacturers
    const sortedManufacturers = useMemo(() => {
        return [...manufacturers].sort((a, b) =>
            a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' })
        )
    }, [manufacturers])

    const getSeriesOptionLabel = (series: Series): string => {
        if (selectedManufacturer) return series.name
        const manufacturerName = manufacturers.find(m => m.id === series.manufacturer_id)?.name || 'Unknown'
        return `${manufacturerName} - ${series.name}`
    }

    // Filtered and Sorted Series based on manufacturer
    const sortedFilteredSeries = useMemo(() => {
        if (selectedManufacturer) {
            return allSeries
                .filter(s => s.manufacturer_id === selectedManufacturer)
                .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }))
        }
        return [...allSeries].sort((a, b) => {
            const manufacturerA = manufacturers.find(m => m.id === a.manufacturer_id)?.name || ''
            const manufacturerB = manufacturers.find(m => m.id === b.manufacturer_id)?.name || ''
            const manufacturerCompare = manufacturerA.localeCompare(manufacturerB, undefined, { numeric: true, sensitivity: 'base' })
            if (manufacturerCompare !== 0) return manufacturerCompare
            return a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' })
        })
    }, [selectedManufacturer, allSeries, manufacturers])

    // Filtered models based on manufacturer and series selection
    const filteredModels = useMemo(() => {
        if (!selectedManufacturer) return []

        let models = allModels

        // Filter by manufacturer objects first
        const manufacturerSeriesIds = allSeries
            .filter(s => s.manufacturer_id === selectedManufacturer)
            .map(s => s.id)
        models = models.filter(m => manufacturerSeriesIds.includes(m.series_id))

        // Filter by series selection
        if (selectedSeriesValue === ALL_SERIES_VALUE) {
            // no-op
        } else if (selectedSeriesIds.length > 0) {
            models = models.filter(m => selectedSeriesIds.includes(m.series_id))
        } else {
            models = []
        }

        return models
    }, [selectedManufacturer, selectedSeriesValue, selectedSeriesIds, allModels, allSeries])

    // Auto-select all models when filtered list changes
    useEffect(() => {
        if (!selectedManufacturer) {
            setSelectedModels(new Set())
            return
        }

        if (filteredModels.length > 0) {
            setSelectedModels(new Set(filteredModels.map(m => m.id)))
        } else {
            setSelectedModels(new Set())
        }
    }, [filteredModels, selectedManufacturer])

    // Handle recalculate prices
    const handleRecalcPrices = async () => {
        if (selectedModels.size === 0) {
            setError('No models selected')
            return
        }

        try {
            setRecalculating(true)
            setError(null)

            const modelIds = Array.from(selectedModels)
            const selected = modelIds
                .map(id => allModels.find(m => m.id === id))
                .filter((m): m is Model => Boolean(m))

            const precheckSkipped: Array<{ modelName: string; reason: string }> = []
            const modelIdsToProcess: number[] = []

            for (const m of selected) {
                const reasons: string[] = []
                if (m.exclude_from_etsy_export) reasons.push('Excluded from Etsy export')

                const missingDimFields: string[] = []
                if (!(typeof m.width === 'number' && m.width > 0)) missingDimFields.push('width')
                if (!(typeof m.depth === 'number' && m.depth > 0)) missingDimFields.push('depth')
                if (!(typeof m.height === 'number' && m.height > 0)) missingDimFields.push('height')

                if (!(typeof m.surface_area_sq_in === 'number' && m.surface_area_sq_in > 0)) {
                    reasons.push(
                        missingDimFields.length > 0
                            ? `Missing required information: ${missingDimFields.join(', ')} (surface_area_sq_in cannot be derived)`
                            : 'Missing required information: surface_area_sq_in'
                    )
                }

                if (reasons.length > 0) {
                    precheckSkipped.push({ modelName: m.name || `Model ${m.id}`, reason: reasons.join('; ') })
                } else {
                    modelIdsToProcess.push(m.id)
                }
            }

            if (precheckSkipped.length > 0) {
                setSelectedModels(new Set(modelIdsToProcess))
                const precheckSummary = [
                    `Models Selected: ${modelIds.length}`,
                    `Models not being processed: ${precheckSkipped.length}`,
                    ...precheckSkipped.map(s => `${s.modelName} | Reason: ${s.reason}`),
                    '',
                    `Models to be processed: ${modelIdsToProcess.length}`,
                    '',
                    'Would you like to change or update models before recalculating?',
                    'Click OK for Yes (cancel now), or Cancel for No (continue).'
                ].join('\n')

                const cancelAndFix = window.confirm(precheckSummary)
                if (cancelAndFix) {
                    setError(null)
                    return
                }
            }

            if (modelIdsToProcess.length === 0) {
                setSelectedModels(new Set())
                setError([
                    'RECALCULATION COMPLETE',
                    `Models selected: ${modelIds.length}`,
                    `Models skipped: ${precheckSkipped.length}`,
                    'Skipped model details:',
                    ...precheckSkipped.map(s => `${s.modelName} | Reason: ${s.reason}`),
                    '',
                    'Models successfully processed: 0',
                ].join('\n'))
                return
            }

            const response = await pricingApi.recalculateBaselines({
                model_ids: modelIdsToProcess,
                only_if_stale: false
            })

            const failedModelIds = new Set<number>((response.errors || []).map(e => e.model_id))
            setSelectedModels(new Set(modelIdsToProcess.filter(id => !failedModelIds.has(id))))

            const selectedCount = modelIds.length
            const skippedCount = precheckSkipped.length + (response.skipped_models ?? 0)

            if (response.errors?.length) {
                const byModel = new Map<number, { name: string; reasons: Set<string> }>()
                for (const e of response.errors) {
                    const model = allModels.find(m => m.id === e.model_id)
                    const name = model?.name || `Model ${e.model_id}`
                    if (!byModel.has(e.model_id)) byModel.set(e.model_id, { name, reasons: new Set<string>() })
                    byModel.get(e.model_id)!.reasons.add(e.message)
                }

                setError([
                    'RECALCULATION COMPLETE',
                    `Models selected: ${selectedCount}`,
                    `Models skipped: ${skippedCount}`,
                    'Skipped model details:',
                    ...precheckSkipped.map(s => `${s.modelName} | Reason: ${s.reason}`),
                    ...Array.from(byModel.values()).map(m => `${m.name} | Reason: ${Array.from(m.reasons).join('; ')}`),
                    '',
                    `Models successfully processed: ${response.recalculated_models}`,
                ].join('\n'))
            } else {
                alert([
                    'RECALCULATION COMPLETE',
                    `Models selected: ${selectedCount}`,
                    `Models skipped: ${skippedCount}`,
                    ...(precheckSkipped.length ? ['Skipped model details:', ...precheckSkipped.map(s => `${s.modelName} | Reason: ${s.reason}`), ''] : []),
                    `Models successfully processed: ${response.recalculated_models}`,
                ].join('\n'))
            }
        } catch (err: any) {
            setError(`Recalculation failed: ${err.message || 'Unknown error'}`)
        } finally {
            setRecalculating(false)
        }
    }

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
                <CircularProgress />
            </Box>
        )
    }

    return (
        <Box>
            <Typography variant="h4" gutterBottom>Etsy Export</Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
                Select models to prepare for Etsy export. Export functionality coming soon.
            </Typography>

            {error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                    <Typography component="div" sx={{ whiteSpace: 'pre-line' }}>
                        {error}
                    </Typography>
                </Alert>
            )}

            <Paper sx={{ p: 3, mt: 3 }}>
                <Typography variant="h6" gutterBottom>Filter Models</Typography>

                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} md={4}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Manufacturer</InputLabel>
                            <Select
                                value={selectedManufacturer}
                                label="Manufacturer"
                                onChange={(e) => {
                                    setSelectedManufacturer(e.target.value as number | '')
                                    // Reset series state
                                    setSelectedSeriesValue('')
                                    setSelectedSeriesIds([])
                                    setSelectedModels(new Set())
                                }}
                            >
                                <MenuItem value="">All Manufacturers</MenuItem>
                                {sortedManufacturers.map(m => (
                                    <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Grid>

                    <Grid item xs={12} md={4}>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Series</InputLabel>
                            <Select
                                multiple
                                value={selectedSeriesValue === ALL_SERIES_VALUE ? [ALL_SERIES_VALUE] : selectedSeriesIds.map(String)}
                                label="Series"
                                onChange={(e) => {
                                    const valuev = e.target.value
                                    // Handle array return from multiple select
                                    const values = typeof valuev === 'string' ? valuev.split(',') : valuev as string[]

                                    // Check if "All Series" was just selected (it will be the last element if recently clicked while others were selected)
                                    const lastSelected = values[values.length - 1]

                                    if (lastSelected === ALL_SERIES_VALUE) {
                                        setSelectedSeriesValue(ALL_SERIES_VALUE)
                                        setSelectedSeriesIds([])
                                        return
                                    }

                                    // Filter out ALL_SERIES_VALUE if mixed with others
                                    const validIds = values
                                        .filter(v => v !== ALL_SERIES_VALUE)
                                        .map(v => Number(v))

                                    let resolvedSeriesIds = validIds
                                    if (!selectedManufacturer && validIds.length > 0) {
                                        const inferredSeries = allSeries.find(s => s.id === validIds[0])
                                        const inferredManufacturerId = inferredSeries?.manufacturer_id
                                        if (inferredManufacturerId) {
                                            setSelectedManufacturer(inferredManufacturerId)
                                            resolvedSeriesIds = validIds.filter((id) => {
                                                const series = allSeries.find(s => s.id === id)
                                                return series?.manufacturer_id === inferredManufacturerId
                                            })
                                        }
                                    }

                                    if (resolvedSeriesIds.length === 0) {
                                        setSelectedSeriesValue('')
                                        setSelectedSeriesIds([])
                                    } else {
                                        setSelectedSeriesValue(MULTI_SERIES_VALUE)
                                        setSelectedSeriesIds(resolvedSeriesIds)
                                    }
                                }}
                                renderValue={(selected) => {
                                    if (selected.length === 0) return 'Select series'
                                    if (selected.includes(ALL_SERIES_VALUE)) {
                                        return (
                                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                                <Chip label="All Series" size="small" />
                                            </Box>
                                        )
                                    }
                                    return (
                                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                            {selected.map((idStr) => {
                                                const s = allSeries.find(ser => ser.id === Number(idStr))
                                                return <Chip key={idStr} label={s ? getSeriesOptionLabel(s) : idStr} size="small" />
                                            })}
                                        </Box>
                                    )
                                }}
                            >
                                <MenuItem value={ALL_SERIES_VALUE}>All Series</MenuItem>
                                {sortedFilteredSeries.map(s => (
                                    <MenuItem key={s.id} value={String(s.id)}>{getSeriesOptionLabel(s)}</MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <Button
                            variant="text"
                            size="small"
                            onClick={() => {
                                setSelectedSeriesValue('')
                                setSelectedSeriesIds([])
                                setSelectedModels(new Set())
                                setError(null)
                            }}
                            disabled={!selectedManufacturer && selectedModels.size === 0}
                        >
                            Clear
                        </Button>
                        </Box>
                    </Grid>

                    <Grid item xs={12} md={4}>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            {selectedManufacturer ? `${selectedModels.size} models selected` : '0 models selected'}
                        </Typography>
                    </Grid>
                </Grid>

                <Button
                    variant="contained"
                    startIcon={recalculating ? <CircularProgress size={20} /> : <RefreshIcon />}
                    onClick={handleRecalcPrices}
                    disabled={selectedModels.size === 0 || recalculating}
                >
                    {recalculating ? 'Recalculating...' : 'Recalc Prices'}
                </Button>
            </Paper>

            <Paper sx={{ width: '100%', mb: 2, mt: 3, p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">Models</Typography>
                    {selectedManufacturer && (
                        <Typography variant="body2" color="text.secondary">
                            Showing {filteredModels.length} models • {selectedModels.size} selected
                        </Typography>
                    )}
                </Box>

                {!selectedManufacturer ? (
                    <Alert severity="info">Select a manufacturer to view models.</Alert>
                ) : (
                    <TableContainer sx={{ maxHeight: 600 }}>
                        <Table stickyHeader size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell padding="checkbox">
                                        <Checkbox
                                            indeterminate={selectedModels.size > 0 && selectedModels.size < filteredModels.length}
                                            checked={filteredModels.length > 0 && selectedModels.size === filteredModels.length}
                                            onChange={() => {
                                                if (selectedModels.size === filteredModels.length && filteredModels.length > 0) {
                                                    setSelectedModels(new Set())
                                                } else {
                                                    setSelectedModels(new Set(filteredModels.map(m => m.id)))
                                                }
                                            }}
                                            disabled={filteredModels.length === 0}
                                        />
                                    </TableCell>
                                    <TableCell>Model Name</TableCell>
                                    <TableCell>Series</TableCell>
                                    <TableCell>Dimensions</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {filteredModels.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={4} align="center" sx={{ py: 3 }}>
                                            <Typography variant="body2" color="text.secondary">
                                                No models found matching the filters.
                                            </Typography>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredModels.map((row) => {
                                        const isSelected = selectedModels.has(row.id);
                                        const seriesName = allSeries.find(s => s.id === row.series_id)?.name || 'Unknown';
                                        return (
                                            <TableRow
                                                hover
                                                role="checkbox"
                                                aria-checked={isSelected}
                                                tabIndex={-1}
                                                key={row.id}
                                                selected={isSelected}
                                                onClick={() => {
                                                    const newSelected = new Set(selectedModels)
                                                    if (newSelected.has(row.id)) {
                                                        newSelected.delete(row.id)
                                                    } else {
                                                        newSelected.add(row.id)
                                                    }
                                                    setSelectedModels(newSelected)
                                                }}
                                                sx={{ cursor: 'pointer' }}
                                            >
                                                <TableCell padding="checkbox">
                                                    <Checkbox
                                                        checked={isSelected}
                                                        onChange={(e) => {
                                                            e.stopPropagation()
                                                            const newSelected = new Set(selectedModels)
                                                            if (newSelected.has(row.id)) {
                                                                newSelected.delete(row.id)
                                                            } else {
                                                                newSelected.add(row.id)
                                                            }
                                                            setSelectedModels(newSelected)
                                                        }}
                                                    />
                                                </TableCell>
                                                <TableCell component="th" scope="row">
                                                    {row.name}
                                                </TableCell>
                                                <TableCell>{seriesName}</TableCell>
                                                <TableCell>{`${row.width || '-'} " x ${row.depth || '-'} " x ${row.height || '-'} "`}</TableCell>
                                            </TableRow>
                                        );
                                    })
                                )}
                            </TableBody>
                        </Table>
                    </TableContainer>
                )}
            </Paper>
        </Box>
    )
}
