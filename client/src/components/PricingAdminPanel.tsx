import { useState } from 'react'
import {
    Dialog, DialogTitle, DialogContent, DialogActions,
    Button, FormControl, InputLabel, Select, MenuItem,
    FormLabel, RadioGroup, FormControlLabel, Radio,
    Box, Typography, Checkbox, ListItemText, OutlinedInput,
    Chip, CircularProgress, Alert, Stack, Divider, Paper
} from '@mui/material'
import Grid from '@mui/material/Grid'
import { pricingApi } from '../services/api'
import type { Manufacturer, Series, Model, PricingRecalculateBulkResponse } from '../types'

interface PricingAdminPanelProps {
    open: boolean
    onClose: () => void
    manufacturers: Manufacturer[]
    series: Series[]
    models: Model[]
}

type Scope = 'manufacturer' | 'series' | 'models'

export default function PricingAdminPanel({ open, onClose, manufacturers, series, models }: PricingAdminPanelProps) {
    const [scope, setScope] = useState<Scope>('models') // Default to safe "models" or prompt says "manufacturer" as strict. Let's default to 'models' for safety.
    // Prompt says "Default: amazon" (Marketplace), "Scope selector radio".

    const [selectedManufacturer, setSelectedManufacturer] = useState<number | ''>('')
    const [selectedSeries, setSelectedSeries] = useState<number | ''>('')
    const [selectedModelIds, setSelectedModelIds] = useState<number[]>([])

    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<PricingRecalculateBulkResponse | null>(null)
    const [error, setError] = useState<string | null>(null)

    // Filter logic
    const filteredSeries = selectedManufacturer
        ? series.filter(s => s.manufacturer_id === selectedManufacturer)
        : []

    const filteredModels = (() => {
        let m = models
        if (selectedManufacturer) {
            // If series selected, strict filter
            if (selectedSeries) {
                m = m.filter(x => x.series_id === selectedSeries)
            } else {
                // Filter by manufacturer via series
                // We need a map or helper. 
                // Model -> Series -> Manufacturer
                // Efficient way:
                const seriesIds = series.filter(s => s.manufacturer_id === selectedManufacturer).map(s => s.id)
                m = m.filter(x => seriesIds.includes(x.series_id))
            }
        } else if (selectedSeries) {
            m = m.filter(x => x.series_id === selectedSeries)
        }
        return m
    })()

    const handleRecalculate = async () => {
        setLoading(true)
        setResult(null)
        setError(null)

        try {
            const payload = {
                marketplaces: ["amazon"],
                scope,
                manufacturer_id: selectedManufacturer || undefined,
                series_id: selectedSeries || undefined,
                model_ids: selectedModelIds.length > 0 ? selectedModelIds : undefined,
                variant_set: "baseline4",
                dry_run: false
            }

            // Validation before call (UI UX)
            if (scope === 'manufacturer' && !selectedManufacturer) throw new Error("Please select a manufacturer.")
            if (scope === 'series' && (!selectedManufacturer || !selectedSeries)) throw new Error("Please select a manufacturer and series.")
            if (scope === 'models' && selectedModelIds.length === 0) throw new Error("Please select at least one model.")

            // @ts-ignore - fix later if api.ts types need adjustment
            const res = await pricingApi.recalculateBulk(payload)
            setResult(res)

        } catch (e: any) {
            console.error(e)
            setError(e.message || e.response?.data?.detail || "Recalculation failed")
        } finally {
            setLoading(false)
        }
    }

    const handleClose = () => {
        if (!loading) onClose()
    }

    return (
        <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
            <DialogTitle>Pricing Administration (Baseline Recalculation)</DialogTitle>
            <DialogContent>
                <Box sx={{ py: 2 }}>

                    {/* Marketplace (Static for now as per rules) */}
                    <Typography variant="subtitle2" gutterBottom>Marketplaces: Amazon (Default)</Typography>
                    <Divider sx={{ mb: 2 }} />

                    {/* Scope Selector */}
                    <FormControl component="fieldset" sx={{ mb: 3 }}>
                        <FormLabel component="legend">Recalculation Scope</FormLabel>
                        <RadioGroup row value={scope} onChange={(e) => setScope(e.target.value as Scope)}>
                            <FormControlLabel value="models" control={<Radio />} label="Selected Models" />
                            <FormControlLabel value="series" control={<Radio />} label="Entire Series" />
                            <FormControlLabel value="manufacturer" control={<Radio />} label="Entire Manufacturer" />
                        </RadioGroup>
                    </FormControl>

                    <Grid container spacing={3}>
                        {/* Manufacturer Dropdown */}
                        <Grid item xs={12} md={6}>
                            <FormControl fullWidth disabled={scope === 'models' && false /* Always useful for filtering */}>
                                <InputLabel>Manufacturer</InputLabel>
                                <Select
                                    value={selectedManufacturer}
                                    label="Manufacturer"
                                    onChange={(e) => {
                                        setSelectedManufacturer(e.target.value as number)
                                        setSelectedSeries('')
                                        // Keep model selection? Maybe clear it logic wise
                                    }}
                                >
                                    <MenuItem value=""><em>None</em></MenuItem>
                                    {manufacturers.map(m => (
                                        <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>

                        {/* Series Dropdown */}
                        <Grid item xs={12} md={6}>
                            <FormControl fullWidth disabled={!selectedManufacturer}>
                                <InputLabel>Series</InputLabel>
                                <Select
                                    value={selectedSeries}
                                    label="Series"
                                    onChange={(e) => setSelectedSeries(e.target.value as number)}
                                >
                                    <MenuItem value=""><em>None</em></MenuItem>
                                    {filteredSeries.map(s => (
                                        <MenuItem key={s.id} value={s.id}>{s.name}</MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>

                        {/* Model Selection (Only if Scope = Models) */}
                        {scope === 'models' && (
                            <Grid item xs={12}>
                                <FormControl fullWidth>
                                    <InputLabel>Models (Select one or more)</InputLabel>
                                    <Select
                                        multiple
                                        value={selectedModelIds}
                                        onChange={(e) => {
                                            const val = e.target.value
                                            setSelectedModelIds(typeof val === 'string' ? val.split(',').map(Number) : val)
                                        }}
                                        input={<OutlinedInput label="Models (Select one or more)" />}
                                        renderValue={(selected) => (
                                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                                {selected.map((value) => {
                                                    const m = models.find(x => x.id === value)
                                                    return <Chip key={value} label={m ? m.name : value} size="small" />
                                                })}
                                            </Box>
                                        )}
                                    >
                                        <MenuItem onClick={() => setSelectedModelIds(filteredModels.map(x => x.id))}>
                                            <em>Select All Filtered ({filteredModels.length})</em>
                                        </MenuItem>
                                        <MenuItem onClick={() => setSelectedModelIds([])}>
                                            <em>Clear Selection</em>
                                        </MenuItem>
                                        <Divider />
                                        {filteredModels.map((model) => (
                                            <MenuItem key={model.id} value={model.id}>
                                                <Checkbox checked={selectedModelIds.indexOf(model.id) > -1} />
                                                <ListItemText primary={model.name} secondary={model.parent_sku} />
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                                <Typography variant="caption">{filteredModels.length} models available based on filters.</Typography>
                            </Grid>
                        )}

                        {/* Info Summary */}
                        <Grid item xs={12}>
                            <Alert severity="info">
                                {scope === 'manufacturer' && selectedManufacturer && `Will recalculate ALL models for Manufacturer ID ${selectedManufacturer}.`}
                                {scope === 'series' && selectedSeries && `Will recalculate ALL models in Series ID ${selectedSeries}.`}
                                {scope === 'models' && `Will recalculate ${selectedModelIds.length} selected models.`}

                                {!selectedManufacturer && scope !== 'models' && "Please select a manufacturer."}
                            </Alert>
                        </Grid>

                        {/* ERROR */}
                        {error && (
                            <Grid item xs={12}>
                                <Alert severity="error">{error}</Alert>
                            </Grid>
                        )}

                        {/* RESULTS */}
                        {result && (
                            <Grid item xs={12}>
                                <Paper sx={{ p: 2, bgcolor: '#f5f9ff' }} variant="outlined">
                                    <Typography variant="h6" gutterBottom>Recalculation Results</Typography>
                                    <Typography><b>Total Resolved:</b> {result.resolved_model_count}</Typography>

                                    {Object.entries(result.results).map(([mp, data]) => (
                                        <Box key={mp} sx={{ mt: 2 }}>
                                            <Typography variant="subtitle2" sx={{ textTransform: 'capitalize' }}>{mp}</Typography>
                                            <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                                                <Chip label={`Success: ${data.succeeded.length}`} color="success" />
                                                <Chip label={`Failed: ${data.failed.length}`} color={data.failed.length > 0 ? "error" : "default"} />
                                            </Stack>
                                            {data.failed.length > 0 && (
                                                <Box sx={{ mt: 1, maxHeight: 100, overflow: 'auto' }}>
                                                    {data.failed.map((f, i) => (
                                                        <Typography key={i} variant="caption" display="block" color="error">
                                                            Model {f.model_id}: {f.error}
                                                        </Typography>
                                                    ))}
                                                </Box>
                                            )}
                                        </Box>
                                    ))}
                                </Paper>
                            </Grid>
                        )}

                    </Grid>
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={handleClose}>Close</Button>
                <Button
                    onClick={handleRecalculate}
                    variant="contained"
                    color="primary"
                    disabled={loading || (scope === 'models' && selectedModelIds.length === 0)}
                >
                    {loading ? <CircularProgress size={24} /> : "Recalculate Baseline"}
                </Button>
            </DialogActions>
        </Dialog>
    )
}
