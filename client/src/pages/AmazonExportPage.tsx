import { useEffect, useState, useMemo } from 'react'
import {
    Box, Typography, Paper, Button, Grid, Checkbox, TextField,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    Alert, CircularProgress, FormControl, InputLabel, Select, MenuItem,
    Chip, IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
    ToggleButton, ToggleButtonGroup, Tooltip, Divider,
    Accordion, AccordionSummary, AccordionDetails, Switch, FormControlLabel, Stack, Radio
} from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import DownloadIcon from '@mui/icons-material/Download'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import RefreshIcon from '@mui/icons-material/Refresh'
import FactCheckIcon from '@mui/icons-material/FactCheck'
import WarningIcon from '@mui/icons-material/Warning'
import ErrorIcon from '@mui/icons-material/Error'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import FolderOpenIcon from '@mui/icons-material/FolderOpen'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import { manufacturersApi, seriesApi, modelsApi, templatesApi, exportApi, pricingApi, settingsApi, equipmentTypesApi, type ExportValidationResponse, type ExportValidationIssue } from '../services/api'
import { pickBaseDirectory, ensureSubdirectory, writeFileAtomic, loadHandle, clearPersistedHandle, getOrPickWritableBaseDirectory } from '../services/fileSystem'
import type { Manufacturer, Series, Model, AmazonProductType, EquipmentType } from '../types'





interface WriteResult {
    key: string
    filename: string
    status: 'success' | 'failed' | 'pending'
    errorMessage?: string
    warning?: string
    verified?: boolean
    verificationReason?: string
}

const normalizeName = (s?: string | null) => (s ?? '').trim().toLowerCase()

const compareByNameThenId = (a: { name?: string | null, id: number }, b: { name?: string | null, id: number }) => {
    const nameA = normalizeName(a.name)
    const nameB = normalizeName(b.name)
    if (nameA < nameB) return -1
    if (nameA > nameB) return 1
    return a.id - b.id
}

const triggerDownloadWithYield = async (fn: () => Promise<void> | void) => {
    await fn()
    await new Promise(resolve => requestAnimationFrame(resolve))
    await new Promise(resolve => setTimeout(resolve, 250))
}

const extractErrorMessage = async (err: any, fallback: string): Promise<string> => {
    const detail = err?.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    if (detail && typeof detail === 'object') {
        if (typeof detail.message === 'string' && detail.message.trim()) return detail.message
        return JSON.stringify(detail)
    }

    const data = err?.response?.data
    if (data instanceof Blob) {
        try {
            const text = await data.text()
            if (text) {
                try {
                    const parsed = JSON.parse(text)
                    const parsedDetail = parsed?.detail ?? parsed?.message
                    if (typeof parsedDetail === 'string' && parsedDetail.trim()) return parsedDetail
                    if (parsedDetail && typeof parsedDetail === 'object') return JSON.stringify(parsedDetail)
                } catch {
                    return text
                }
            }
        } catch {
            // ignore blob parsing failure
        }
    }

    return err?.message || fallback
}

const parseExportWarnings = (headers: any): string[] => {
    const raw =
        headers?.['x-export-warnings'] ??
        headers?.['X-Export-Warnings'] ??
        null
    if (!raw) return []

    try {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) {
            return parsed.filter((v): v is string => typeof v === 'string' && v.trim().length > 0)
        }
        return []
    } catch {
        return []
    }
}

const sanitizeFilenameToken = (value: string): string => {
    const trimmed = (value || '').trim()
    if (!trimmed) return 'Unknown'
    return trimmed
        .replace(/\s+/g, '_')
        .replace(/[<>:"/\\|?*\x00-\x1F]/g, '')
}

// Sentinel value for "All Series" to avoid type mixing in Select
const ALL_SERIES_VALUE = '__ALL_SERIES__'
// Sentinel value for "Multi Series" mode (internal state usage)
const MULTI_SERIES_VALUE = '__MULTI__'

export default function AmazonExportPage() {
    const [manufacturers, setManufacturers] = useState<Manufacturer[]>([])
    const [allSeries, setAllSeries] = useState<Series[]>([])
    const [allModels, setAllModels] = useState<Model[]>([])
    const [allEquipmentTypes, setAllEquipmentTypes] = useState<EquipmentType[]>([])
    const [templates, setTemplates] = useState<AmazonProductType[]>([])
    const [equipmentTypeLinks, setEquipmentTypeLinks] = useState<{ equipment_type_id: number, product_type_id: number }[]>([])
    // Phase 7: Export Settings
    const [exportSettings, setExportSettings] = useState<{ id: number; default_save_path_template?: string; amazon_customization_export_format?: string } | null>(null)
    const [localSavePathTemplate, setLocalSavePathTemplate] = useState('')

    const [selectedManufacturer, setSelectedManufacturer] = useState<number | ''>('')
    const [selectedSeries, setSelectedSeries] = useState<number | ''>('')
    const [selectedSeriesValue, setSelectedSeriesValue] = useState<string>('') // Controlled Select value
    const [selectedSeriesIds, setSelectedSeriesIds] = useState<number[]>([])
    const [selectedModels, setSelectedModels] = useState<Set<number>>(new Set())

    const [loading, setLoading] = useState(true)
    const [recalculating, setRecalculating] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [missingSnapshots, setMissingSnapshots] = useState<Record<number, string[]> | null>(null)

    const [listingType, setListingType] = useState<'individual' | 'parent_child'>('individual')
    const [downloading, setDownloading] = useState<string | null>(null)
    const [includeCustomization] = useState(true)

    // Phase 9: File System Access
    const [baseDir, setBaseDir] = useState<any | null>(null) // Using any to avoid strict type ref issues if libs mismatch, though typed in service
    const [fsStatus, setFsStatus] = useState<string | null>(null)
    const [writeResults, setWriteResults] = useState<WriteResult[]>([])
    const [lastSavePlanSnapshot, setLastSavePlanSnapshot] = useState<any | null>(null) // Store plan for retry reliability



    // Phase 12: Export Confidence Verification


    // Phase 13A: Validation
    const [validating, setValidating] = useState(false)
    const [validationReport, setValidationReport] = useState<ExportValidationResponse | null>(null)
    const [postExportImageWarnings, setPostExportImageWarnings] = useState<ExportValidationIssue[]>([])

    // Phase 14A: Validation Caching
    const [lastValidationKey, setLastValidationKey] = useState<string | null>(null)
    const [lastValidationAtMs, setLastValidationAtMs] = useState<number | null>(null)
    const VALIDATION_TTL_MS = 60000

    // Phase 14A: Load Instumentation
    const [loadStep, setLoadStep] = useState<string>('Starting')
    const [loadError, setLoadError] = useState<string | null>(null)

    // Customization Format State
    const [customizationDefaultFormat, setCustomizationDefaultFormat] = useState<'txt' | 'xlsx'>('xlsx')
    const [productDefaultFormat, setProductDefaultFormat] = useState<'csv' | 'xlsx'>('xlsx')
    const [runningBoth, setRunningBoth] = useState(false)
    const [runBothProgress, setRunBothProgress] = useState<string>('')

    // Legacy Alias (Maintains compatibility)
    const localCustomizationFormat = customizationDefaultFormat
    const setLocalCustomizationFormat = (fmt: string) => setCustomizationDefaultFormat(fmt as 'txt' | 'xlsx')
    const [custCopyCopied, setCustCopyCopied] = useState(false)

    const [quickCsvFields, setQuickCsvFields] = useState({
        asin: false,
        sku: false,
        manufacturer: false,
        series: false,
        model: false,
        equipment_type: false
    })
    const [includeHeaders, setIncludeHeaders] = useState(false)
    const [quickCsvHeaders, setQuickCsvHeaders] = useState({
        asin: 'ASIN',
        sku: 'SKU',
        manufacturer: 'Manufacturer Name',
        series: 'Series Name',
        model: 'Model Name',
        equipment_type: 'Equipment Type'
    })

    const buildAmazonExportFilenameBase = (includeCustomizationSuffix = false): string => {
        const selectedModelRecords = Array.from(selectedModels)
            .map(id => allModels.find(m => m.id === id))
            .filter((m): m is Model => Boolean(m))

        const manufacturerNameFromSelection =
            manufacturers.find(m => m.id === selectedManufacturer)?.name || ''

        const seriesIds = new Set<number>()
        selectedModelRecords.forEach(m => seriesIds.add(m.series_id))
        const selectedSeriesRecords = allSeries.filter(s => seriesIds.has(s.id))

        let manufacturerName = manufacturerNameFromSelection
        if (!manufacturerName && selectedSeriesRecords.length > 0) {
            const mfrId = selectedSeriesRecords[0].manufacturer_id
            manufacturerName = manufacturers.find(m => m.id === mfrId)?.name || ''
        }
        if (!manufacturerName) manufacturerName = 'Unknown_Manufacturer'

        let seriesToken = 'Unknown_Series'
        if (selectedSeriesRecords.length > 1) {
            seriesToken = 'Multiple_Series'
        } else if (selectedSeriesRecords.length === 1) {
            seriesToken = selectedSeriesRecords[0].name || 'Unknown_Series'
        }

        const now = new Date()
        const dateToken = `${now.getFullYear()}-${now.getMonth() + 1}-${now.getDate()}`
        const mfrToken = sanitizeFilenameToken(manufacturerName)
        const seriesTokenSanitized = sanitizeFilenameToken(seriesToken)

        if (includeCustomizationSuffix) {
            return `Amazon_${mfrToken}_${seriesTokenSanitized}_Customization_${dateToken}`
        }
        return `Amazon_${mfrToken}_${seriesTokenSanitized}_${dateToken}`
    }

    // Computed Status Logic (Phase 4 - Chunk 3)
    const missingTemplateNames = useMemo(() => {
        if (!includeCustomization) return []
        const missingSet = new Set<string>()
        selectedModels.forEach(modelId => {
            const model = allModels.find(m => m.id === modelId)
            if (model) {
                const et = allEquipmentTypes.find(e => e.id === model.equipment_type_id)
                // If ET missing OR template assignment missing, it's a "missing" case
                if (!et || !et.amazon_customization_template_id) {
                    missingSet.add(et ? et.name : `Unknown Equipment Type (ID: ${model.equipment_type_id})`)
                }
            }
        })
        return Array.from(missingSet)
    }, [includeCustomization, selectedModels, allModels, allEquipmentTypes])



    useEffect(() => {
        loadData()
        loadHandle().then(h => { if (h) setBaseDir(h) })
    }, [])

    const loadData = async () => {
        // Watchdog
        const watchdog = setTimeout(() => {
            setLoading(prev => {
                if (prev) {
                    console.error('[EXPORT] Initialization Timeout (15s)')
                    setLoadError('Initialization timed out (15s). Please check your connection.')
                    return false
                }
                return prev
            })
        }, 15000)

        try {
            setLoading(true)
            setLoadError(null)

            console.log('[EXPORT] Starting Data Load')
            setLoadStep('Fetching API Data...')

            const [mfrs, series, models, eqTypes, tmpls, links, expSettings] = await Promise.all([
                manufacturersApi.list().catch((e: any) => { throw new Error(`Manufacturers: ${e.message}`) }),
                seriesApi.list().catch((e: any) => { throw new Error(`Series: ${e.message}`) }),
                modelsApi.list().catch((e: any) => { throw new Error(`Models: ${e.message}`) }),
                equipmentTypesApi.list().catch((e: any) => { throw new Error(`Equipment Types: ${e.message}`) }),
                templatesApi.list().catch((e: any) => { throw new Error(`Templates: ${e.message}`) }),
                templatesApi.listEquipmentTypeLinks().catch((e: any) => { throw new Error(`Links: ${e.message}`) }),
                settingsApi.getExport().catch((e: any) => { throw new Error(`Settings: ${e.message}`) })
            ])

            console.log('[EXPORT] Data Load Complete')
            setLoadStep('Processing Data...')

            setManufacturers(mfrs)
            setAllSeries(series)
            setAllModels(models)
            setAllEquipmentTypes(eqTypes)
            setTemplates(tmpls)
            setEquipmentTypeLinks(links)
            setExportSettings(expSettings)
            setLocalSavePathTemplate(expSettings.default_save_path_template || '')
            setLocalCustomizationFormat(expSettings.amazon_customization_export_format || 'xlsx')

        } catch (err: any) {
            console.error('[EXPORT] Data Load Failed', err)
            setLoadError(err.message || 'Failed to initialize export data')
            setError('Failed to load data')
        } finally {
            clearTimeout(watchdog)
            setLoading(false)
        }
    }



    const handleSaveExportSettings = async () => {
        try {
            const updated = await settingsApi.updateExport({
                default_save_path_template: localSavePathTemplate,
                amazon_customization_export_format: localCustomizationFormat
            })
            setExportSettings(updated)
            alert('Export configuration saved.')
        } catch (err) {
            console.error(err)
            alert('Failed to save export configuration')
        }
    }

    // ... (previous filter logic)

    // Compute Save Plan
    const savePlan = useMemo(() => {
        if (!selectedManufacturer || selectedModels.size === 0 || !exportSettings?.default_save_path_template) {
            return null
        }

        const mfrName = manufacturers.find(m => m.id === selectedManufacturer)?.name || 'Unknown'
        const marketplace = 'Amazon' // Static for now

        // Determine involved series
        const involvedSeriesIds = new Set<number>()
        selectedModels.forEach(mid => {
            const model = allModels.find(m => m.id === mid)
            if (model) involvedSeriesIds.add(model.series_id)
        })

        const involvedSeries = allSeries.filter(s => involvedSeriesIds.has(s.id))
        const isMultiSeries = involvedSeries.length > 1

        const replacePlaceholders = (template: string, seriesName: string) => {
            return template
                .replace(/\[Manufacturer_Name\]/g, mfrName)
                .replace(/\[Series_Name\]/g, seriesName)
                .replace(/\[Marketplace\]/g, marketplace)
                // Basic sanitization
                .replace(/[<>"|?*]/g, '') // Kept : and / for path separation
        }

        const basePath = exportSettings.default_save_path_template

        if (isMultiSeries) {
            // Master Plan
            // Note: We might not have a specific Series Name for the master file path if the template uses [Series_Name]
            // The prompt says: master folder: Base\[Manufacturer]\[Marketplace]-[Manufacturer]-Multi-Series.xlsx
            // But the path comes from the template. 
            // If template is "C:\Exports\[Manufacturer]\[Series]", then master path is ambiguous.
            // We will assume the User's template path ends in a folder structure, and we append filenames.

            // Prompt Rule: 
            // Master: Base\[Manufacturer]\[Marketplace]-[Manufacturer]-Multi-Series.xlsx
            // We'll try to deduce "Base" from the template. 
            // Actually the Template IS the path. 
            // "Example value: ...\Listings\[Manufacturer_Name]\[Series_Name]"

            // So for Single Series: Path = Template. File = [Marketplace]-[Manufacturer]-[Series].xlsx
            // For Multi Series: 
            //   Master Path = Template (but what is Series_Name?). 
            //   Prompt says: "folder: Base\[Manufacturer]\[Series]"

            // Let's interpret the template as the folder path.
            // If template has [Series_Name], we can't resolve it for a multi-series master file easily unless we say "Multi-Series" is the series name.

            const masterSeriesName = "Multi-Series"
            const masterFolder = replacePlaceholders(basePath, masterSeriesName)
            const masterFile = `${marketplace}-${mfrName.replace(/\s+/g, '_')}-Multi_Series.xlsx`

            const perSeriesPlans = involvedSeries.map(s => {
                const folder = replacePlaceholders(basePath, s.name)
                const filename = `${marketplace}-${mfrName.replace(/\s+/g, '_')}-${s.name.replace(/\s+/g, '_')}.xlsx`
                return { folder, filename, seriesId: s.id }
            })

            return {
                type: 'multi',
                master: { folder: masterFolder, filename: masterFile },
                children: perSeriesPlans
            }
        } else {
            // Single Series
            const series = involvedSeries[0]
            if (!series) return null

            const folder = replacePlaceholders(basePath, series.name)
            const filename = `${marketplace}-${mfrName.replace(/\s+/g, '_')}-${series.name.replace(/\s+/g, '_')}.xlsx`

            return {
                type: 'single',
                plan: { folder, filename }
            }
        }
    }, [selectedManufacturer, selectedModels, exportSettings, manufacturers, allSeries, allModels])

    // ... (previous render logic)



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

    const filteredModels = useMemo(() => {
        if (!selectedManufacturer) return []

        let models = allModels

        // Filter by manufacturer objects first
        const manufacturerSeriesIds = allSeries
            .filter(s => s.manufacturer_id === selectedManufacturer)
            .map(s => s.id)
        models = models.filter(m => manufacturerSeriesIds.includes(m.series_id))

        // Filter by series selection:
        // - All Series selected => keep all manufacturer models
        // - Explicit series selected => filter to those
        // - Nothing selected => show none
        if (selectedSeriesValue === ALL_SERIES_VALUE) {
            // no-op
        } else if (selectedSeriesIds.length > 0) {
            models = models.filter(m => selectedSeriesIds.includes(m.series_id))
        } else {
            models = []
        }

        // Deterministic Sort for Display: Name A-Z (case-insensitive), then ID
        return [...models].sort(compareByNameThenId)
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

    const getTemplateForEquipmentType = (equipmentTypeId: number): string | undefined => {
        const link = equipmentTypeLinks.find(l => l.equipment_type_id === equipmentTypeId)
        if (!link) return undefined
        const template = templates.find(t => t.id === link.product_type_id)
        return template?.code
    }

    const getSeriesName = (seriesId: number): string => {
        const series = allSeries.find(s => s.id === seriesId)
        return series?.name || 'Unknown'
    }

    const getManufacturerName = (seriesId: number): string => {
        const series = allSeries.find(s => s.id === seriesId)
        if (!series) return 'Unknown'
        const mfr = manufacturers.find(m => m.id === series.manufacturer_id)
        return mfr?.name || 'Unknown'
    }

    const handleSelectAll = (checked: boolean) => {
        if (checked) {
            setSelectedModels(new Set(filteredModels.map(m => m.id)))
        } else {
            setSelectedModels(new Set())
        }
    }

    const handleSelectModel = (modelId: number, checked: boolean) => {
        const newSelected = new Set(selectedModels)
        if (checked) {
            newSelected.add(modelId)
        } else {
            newSelected.delete(modelId)
        }
        setSelectedModels(newSelected)
    }

    const handleRecalculateSelected = async () => {
        if (selectedModels.size === 0) return
        try {
            setRecalculating(true)
            setError(null)
            const modelIds = Array.from(selectedModels)

            const selected = modelIds
                .map(id => allModels.find(m => m.id === id))
                .filter((m): m is Model => Boolean(m))

            const precheckSkipped: Array<{ modelId: number; modelName: string; reason: string }> = []
            const modelIdsToProcess: number[] = []

            for (const m of selected) {
                const reasons: string[] = []

                if (m.exclude_from_amazon_export) {
                    reasons.push('Excluded from Amazon export')
                }

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
                    precheckSkipped.push({
                        modelId: m.id,
                        modelName: m.name || `Model ${m.id}`,
                        reason: reasons.join('; ')
                    })
                } else {
                    modelIdsToProcess.push(m.id)
                }
            }

            if (precheckSkipped.length > 0) {
                // Keep selection aligned with what can actually be processed.
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
                    // User chose to stop and fix models; do not duplicate the prompt in-page.
                    setError(null)
                    return
                }
            }

            if (modelIdsToProcess.length === 0) {
                setSelectedModels(new Set())
                const noProcessMessage = [
                    'RECALCULATION COMPLETE',
                    `Models selected: ${modelIds.length}`,
                    `Models not being processed: ${precheckSkipped.length}`,
                    'Skipped model details:',
                    ...precheckSkipped.map(s => `${s.modelName} | Reason: ${s.reason}`),
                    '',
                    'Models to be processed: 0',
                    'Models successfully processed: 0',
                ].join('\n')
                setError(noProcessMessage)
                return
            }

            const response = await pricingApi.recalculateBaselines({
                model_ids: modelIdsToProcess,
                only_if_stale: false
            })

            const selectedCount = modelIds.length
            const skippedCount = precheckSkipped.length + (response.skipped_models ?? 0)
            if (response.errors?.length) {
                const failedModelIds = new Set<number>(response.errors.map(e => e.model_id))
                setSelectedModels(new Set(modelIdsToProcess.filter(id => !failedModelIds.has(id))))

                const byModel = new Map<number, { name: string; reasons: Set<string> }>()
                for (const e of response.errors) {
                    const model = allModels.find(m => m.id === e.model_id)
                    const name = model?.name || `Model ${e.model_id}`
                    if (!byModel.has(e.model_id)) {
                        byModel.set(e.model_id, { name, reasons: new Set<string>() })
                    }

                    let reason = e.message
                    const msg = (e.message || '').toLowerCase()
                    if (msg.includes('surface_area_sq_in')) {
                        reason = 'Missing required information: surface_area_sq_in (derived from dimensions W, D, H)'
                    } else if (msg.includes('missing active material assignment for role')) {
                        const role = e.message.split(':').pop()?.trim()
                        reason = `Missing required information: material role assignment (${role})`
                    }
                    byModel.get(e.model_id)!.reasons.add(reason)
                }

                const skippedLines = [
                    ...precheckSkipped.map(s => `${s.modelName} | Reason: ${s.reason}`),
                    ...Array.from(byModel.values()).map(m =>
                    `${m.name} | Reason: ${Array.from(m.reasons).join('; ')}`
                    )
                ]

                const message = [
                    'RECALCULATION COMPLETE',
                    `Models selected: ${selectedCount}`,
                    `Models skipped: ${skippedCount}`,
                    'Skipped model details:',
                    ...skippedLines,
                    '',
                    `Models successfully processed: ${response.recalculated_models}`,
                ].join('\n')
                setError(message)
            } else {
                const successMessage = [
                    'RECALCULATION COMPLETE',
                    `Models selected: ${selectedCount}`,
                    `Models skipped: ${skippedCount}`,
                    ...(precheckSkipped.length
                        ? ['Skipped model details:', ...precheckSkipped.map(s => `${s.modelName} | Reason: ${s.reason}`), '']
                        : []),
                    `Models successfully processed: ${response.recalculated_models}`,
                ].join('\n')
                alert(successMessage)
            }
        } catch (err: any) {
            const msg = await extractErrorMessage(err, 'Failed to recalculate')
            setError(msg)
            console.error(err)
        } finally {
            setRecalculating(false)
        }
    }



    const getFreshValidationReport = async (): Promise<ExportValidationResponse> => {
        // Construct deterministc key for current scope
        const ids = Array.from(selectedModels).sort((a, b) => a - b).join(',')
        const currentKey = `${selectedManufacturer}-${selectedSeries}-${listingType}-${ids}`
        const now = Date.now()

        // Check Cache
        if (validationReport && lastValidationKey === currentKey && lastValidationAtMs && (now - lastValidationAtMs < VALIDATION_TTL_MS)) {
            return validationReport
        }

        // Cache Miss - Fetch Fresh
        const report = await exportApi.validateExport(Array.from(selectedModels), listingType)
        setValidationReport(report)
        setLastValidationKey(currentKey)
        setLastValidationAtMs(now)
        return report
    }

    const handleValidateExport = async () => {
        try {
            setValidating(true)
            // Do not clear validationReport immediately to avoid flicker if cached
            await getFreshValidationReport()
        } catch (err) {
            console.error(err)
            setError("Failed to run validation check")
            setValidationReport(null) // Clear if failed
        } finally {
            setValidating(false)
        }
    }




    const handleFileSystemDownload = async (format: 'xlsx' | 'xlsm' | 'csv', retryMode = false) => {
        console.log(`[EXPORT][${format.toUpperCase()}] click: start`);
        console.trace(`[EXPORT][${format.toUpperCase()}] click stack`);
        try {
            setDownloading(format)

            // Explicit XLSM Branch: Bypass File System API (Fix for Windows Env)
            if (format === 'xlsm') {
                console.log("[EXPORT][XLSM] bypassing file system picker");
                setError(null);
                setFsStatus("Generating XLSM...");
                const modelIds = Array.from(selectedModels);

                try {
                    // Direct Browser Download
                    const response = await exportApi.downloadXlsm(modelIds, listingType);
                    const warnings = parseExportWarnings(response.headers)

                    // Extract filename from headers or default
                    let filename = "Amazon_Export.xlsm";
                    const disposition = response.headers['content-disposition'];
                    if (disposition && disposition.indexOf('attachment') !== -1) {
                        const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                        const matches = filenameRegex.exec(disposition);
                        if (matches != null && matches[1]) {
                            filename = matches[1].replace(/['"]/g, '');
                        }
                    } else {
                        filename = `${buildAmazonExportFilenameBase()}.xlsm`
                    }

                    // Updates for verification stats
                    // Updates for verification stats - REMOVED


                    // Trigger Download
                    const contentType = response.headers['content-type'] || 'application/vnd.ms-excel.sheet.macroEnabled.12';
                    const blob = new Blob([response.data], { type: contentType });

                    // Safety: If blob is JSON, it means backend errored despite 200 (or axios logic mishandled)
                    if (contentType.includes('application/json')) {
                        const text = await response.data.text();
                        throw new Error(`Server returned JSON instead of file: ${text.substring(0, 100)}`);
                    }

                    // Fix extension based on content type (Backend may return XLSX now)
                    const isXlsx = contentType.includes('spreadsheetml.sheet');
                    const targetExt = isXlsx ? '.xlsx' : '.xlsm';

                    // Remove potential existing extension to avoid duplication (e.g. .xlsx.xlsm)
                    filename = filename.replace(/\.(xlsx|xlsm)$/i, '');
                    filename += targetExt;

                    const url = window.URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.setAttribute('download', filename);
                    document.body.appendChild(link);
                    link.click();

                    // Cleanup
                    setTimeout(() => {
                        link.parentNode?.removeChild(link);
                        window.URL.revokeObjectURL(url);
                    }, 100);

                    if (warnings.length) {
                        setError([
                            'Export completed with warnings:',
                            ...warnings,
                        ].join('\n'))
                    }

                    setFsStatus("Download started.");
                    setTimeout(() => setFsStatus(null), 3000);

                } catch (e: any) {
                    console.error("[EXPORT][XLSM] download failed", e);
                    const msg = await extractErrorMessage(e, "Download failed")
                    setError("Download failed: " + msg);
                } finally {
                    setDownloading(null);
                }
                return;
            }

            // Explicit XLSX Branch: Browser Download
            if (format === 'xlsx') {
                console.log("[EXPORT][XLSX] bypassing file system picker");
                setError(null);
                setFsStatus("Generating XLSX...");
                const modelIds = Array.from(selectedModels);
                console.log(`[EXPORT][XLSX] modelIds.length=${modelIds.length} modelIds=${modelIds.join(',')}`);
                console.log(`[EXPORT][XLSX] listingType=${listingType}`);
                console.log(`[EXPORT][XLSX] format=${format}`);

                if (!modelIds || modelIds.length === 0) {
                    console.warn("[EXPORT][XLSX] blocked: no models selected");
                    setError("Select at least one model to export.");
                    setDownloading(null);
                    setFsStatus(null);
                    return;
                }

                if (!listingType) {
                    console.warn("[EXPORT][XLSX] blocked: listingType missing");
                    setError("Listing type is missing. Refresh the page and try again.");
                    setDownloading(null);
                    setFsStatus(null);
                    return;
                }

                console.log("[EXPORT][XLSX] calling downloadXlsx with args:", { modelIds, listingType });

                try {
                    const response = await exportApi.downloadXlsx(modelIds, listingType);
                    const warnings = parseExportWarnings(response.headers)

                    let filename = "Amazon_Export.xlsx";
                    const disposition = response.headers['content-disposition'];
                    if (disposition && disposition.indexOf('attachment') !== -1) {
                        const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                        const matches = filenameRegex.exec(disposition);
                        if (matches != null && matches[1]) {
                            filename = matches[1].replace(/['"]/g, '');
                        }
                    } else {
                        filename = `${buildAmazonExportFilenameBase()}.xlsx`
                    }




                    // XLSX Blob Config
                    const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

                    if (response.headers['content-type']?.includes('application/json')) {
                        const text = await response.data.text();
                        throw new Error(`Server returned JSON instead of file: ${text.substring(0, 100)}`);
                    }

                    if (!filename.toLowerCase().endsWith('.xlsx')) {
                        filename += '.xlsx';
                    }

                    const url = window.URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.setAttribute('download', filename);
                    document.body.appendChild(link);
                    link.click();

                    setTimeout(() => {
                        link.parentNode?.removeChild(link);
                        window.URL.revokeObjectURL(url);
                    }, 100);

                    if (warnings.length) {
                        setError([
                            'Export completed with warnings:',
                            ...warnings,
                        ].join('\n'))
                    }

                    setFsStatus("Download started.");
                    setTimeout(() => setFsStatus(null), 3000);

                } catch (e: any) {
                    console.error("[EXPORT][XLSX] download failed", e);
                    console.error("[EXPORT][XLSX] failed status=", e?.response?.status);
                    console.error("[EXPORT][XLSX] failed data=", e?.response?.data);
                    console.error("[EXPORT][XLSX] failed detail=", e?.response?.data?.detail);
                    const msg = await extractErrorMessage(e, "Download failed")
                    setError("Download failed: " + msg);
                } finally {
                    setDownloading(null);
                }
                return;
            }

            // Explicit CSV Branch: Browser Download
            if (format === 'csv') {
                console.log("[EXPORT][CSV] bypassing file system picker");
                setError(null);
                setFsStatus("Generating CSV...");
                const modelIds = Array.from(selectedModels);

                try {
                    const response = await exportApi.downloadCsv(modelIds, listingType);
                    const warnings = parseExportWarnings(response.headers)

                    let filename = "Amazon_Export.csv";
                    const disposition = response.headers['content-disposition'];
                    if (disposition && disposition.indexOf('attachment') !== -1) {
                        const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                        const matches = filenameRegex.exec(disposition);
                        if (matches != null && matches[1]) {
                            filename = matches[1].replace(/['"]/g, '');
                        }
                    } else {
                        filename = `${buildAmazonExportFilenameBase()}.csv`
                    }




                    // CSV Blob Config
                    const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });

                    if (response.headers['content-type']?.includes('application/json')) {
                        const text = await response.data.text();
                        throw new Error(`Server returned JSON instead of file: ${text.substring(0, 100)}`);
                    }

                    if (!filename.toLowerCase().endsWith('.csv')) {
                        filename += '.csv';
                    }

                    const url = window.URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.setAttribute('download', filename);
                    document.body.appendChild(link);
                    link.click();

                    setTimeout(() => {
                        link.parentNode?.removeChild(link);
                        window.URL.revokeObjectURL(url);
                    }, 100);

                    if (warnings.length) {
                        setError([
                            'Export completed with warnings:',
                            ...warnings,
                        ].join('\n'))
                    }

                    setFsStatus("Download started.");
                    setTimeout(() => setFsStatus(null), 3000);

                } catch (e: any) {
                    console.error("[EXPORT][CSV] download failed", e);
                    const msg = await extractErrorMessage(e, "Download failed")
                    setError("Download failed: " + msg);
                } finally {
                    setDownloading(null);
                }
                return;
            }

            // REGRESSION GUARD: XLSM/XLSX/CSV must NEVER reach this point.
            // If the above "return" is bypassed, we must fail loudly rather than trigger the Folder Picker.
            if (format === 'xlsm' || format === 'xlsx' || format === 'csv') {
                throw new Error(`[EXPORT][${(format as string).toUpperCase()}] Regression detected: File System API invoked for browser download`);
            }

            setError(null)
            setFsStatus(retryMode ? "Retrying failed files..." : "Checking permissions...")
            if (!retryMode) {
                setWriteResults([])
                setLastSavePlanSnapshot(savePlan) // Snapshot key for retry
                setPostExportImageWarnings([]) // Clear previous run warnings
            }

            // specific reference to plan to use
            const activePlan = retryMode ? (lastSavePlanSnapshot || savePlan) : savePlan

            // Track local results to update state at end (or incrementally if we wanted)
            const currentResults: WriteResult[] = retryMode ? [...writeResults] : []

            let debugCurrentFile = "initialization"

            try {
                let runValidationIssues: ExportValidationIssue[] = []
                // 0. Validation Check (Silent Run during export to ensure we catch image issues)
                // Only run if we don't have a fresh report or if we want to be sure.
                // Given the requirement to capture "validation report used", let's re-run or use existing?
                // Re-running ensures we catch transient HTTP failures.
                setFsStatus("Validating...")
                setFsStatus("Validating...")
                try {
                    const freshReport = await getFreshValidationReport()
                    // Filter for image failure warnings
                    // Look for message containing "Image URL inaccessible" or "Unresolved placeholder"
                    runValidationIssues = freshReport.items.filter(i =>
                        i.severity === 'warning' &&
                        (i.message.includes("Image URL inaccessible") || i.message.includes("Unresolved placeholder"))
                    )
                } catch (e) {
                    console.warn("Silent validation failed", e)
                    // Don't block export on validation crash
                }

                setFsStatus("Writing files...");

                // 1. Ensure Base Folder (load, verify, or pick)
                // 1. Ensure Base Folder (load, verify, or pick)
                let dirHandle
                try {
                    dirHandle = await getOrPickWritableBaseDirectory(baseDir)
                    setBaseDir(dirHandle) // Update state if it changed or verified
                } catch (e: any) {
                    // If it's an abort error, just stop silently or show "Cancelled"
                    if (e.name === 'AbortError' || e.message?.includes('aborted')) {
                        console.log("[EXPORT][FS] picker cancelled");
                        setDownloading(null)
                        setFsStatus(null)
                        return
                    }
                    throw e // Propagate real errors
                }

                const modelIds = Array.from(selectedModels)

                // Helper to fix extension
                const getExtension = (fmt: string) => fmt === 'xlsx' ? 'xlsx' : fmt === 'xlsm' ? 'xlsm' : 'csv'
                const ext = getExtension(format)
                const fixExt = (name: string) => name.replace(/\.xlsx$/i, `.${ext}`)



                setFsStatus("Writing files...");

                // Helper to update result list
                const updateResult = (key: string, filename: string, status: 'success' | 'failed', error?: string, warning?: string, verifyResult?: { verified: boolean, reason?: string }) => {
                    const idx = currentResults.findIndex(r => r.key === key)
                    const entry: WriteResult = {
                        key,
                        filename,
                        status,
                        errorMessage: error,
                        warning,
                        verified: verifyResult?.verified,
                        verificationReason: verifyResult?.reason
                    }

                    if (idx >= 0) {
                        currentResults[idx] = entry
                    } else {
                        currentResults.push(entry)
                    }
                    setWriteResults([...currentResults])
                }

                // Helper to check if we should process this key (for retry logic)
                const shouldProcess = (key: string) => {
                    if (!retryMode) return true
                    const existing = writeResults.find(r => r.key === key)
                    return existing?.status === 'failed'
                }

                if (activePlan?.type === 'multi') {
                    // Master
                    const masterKey = 'master'
                    if (shouldProcess(masterKey)) {
                        setFsStatus("Processing Master File...")
                        try {
                            // Fetch Master Blob
                            let masterRes;
                            if (format === 'xlsx') masterRes = await exportApi.downloadXlsx(modelIds, listingType)
                            else if (format === 'xlsm') masterRes = await exportApi.downloadXlsm(modelIds, listingType)
                            else masterRes = await exportApi.downloadCsv(modelIds, listingType)



                            const masterFolderParts = activePlan.master!.folder.split(/[\\/]/).filter((p: string) => p)
                            const masterDir = await ensureSubdirectory(dirHandle, masterFolderParts)

                            debugCurrentFile = "Master File (" + activePlan.master!.filename + ")"
                            const result = await writeFileAtomic(masterDir, fixExt(activePlan.master!.filename), new Blob([masterRes.data]))
                            if (result.warning) console.warn(result.warning)

                            updateResult(masterKey, activePlan.master!.filename, 'success', undefined, result.warning, undefined)
                        } catch (e: any) {
                            console.error("Master write failed", e)
                            updateResult(masterKey, activePlan.master!.filename, 'failed', e.message || 'Write failed')
                        }
                    }

                    // Children
                    let count = 0
                    for (const child of activePlan.children!) {
                        count++
                        const childKey = `series-${(child as any).seriesId}`

                        if (!shouldProcess(childKey)) continue

                        setFsStatus(`Writing Series ${count}/${activePlan.children!.length}: ${child.filename}...`)

                        const childSeriesId = (child as any).seriesId
                        if (!childSeriesId) continue

                        const childModels = modelIds.filter(mid => {
                            const m = allModels.find(am => am.id === mid)
                            return m?.series_id === childSeriesId
                        })

                        if (childModels.length === 0) continue

                        try {
                            let childRes;
                            if (format === 'xlsx') childRes = await exportApi.downloadXlsx(childModels, listingType)
                            else if (format === 'xlsm') childRes = await exportApi.downloadXlsm(childModels, listingType)
                            else childRes = await exportApi.downloadCsv(childModels, listingType)

                            const childFolderParts = child.folder.split(/[\\/]/).filter((p: string) => p)
                            const childDir = await ensureSubdirectory(dirHandle, childFolderParts)

                            debugCurrentFile = "Series File (" + child.filename + ")"
                            const result = await writeFileAtomic(childDir, fixExt(child.filename), new Blob([childRes.data]))
                            if (result.warning) console.warn(result.warning)

                            updateResult(childKey, child.filename, 'success', undefined, result.warning, undefined)
                        } catch (e: any) {
                            console.error(`Series ${childSeriesId} write failed`, e)
                            updateResult(childKey, child.filename, 'failed', e.message || 'Write failed')
                        }
                    }

                } else if (activePlan?.type === 'single') {
                    const key = 'single'
                    if (shouldProcess(key)) {
                        setFsStatus("Writing file...")
                        try {
                            let res;
                            if (format === 'xlsx') res = await exportApi.downloadXlsx(modelIds, listingType)
                            else if (format === 'xlsm') res = await exportApi.downloadXlsm(modelIds, listingType)
                            else res = await exportApi.downloadCsv(modelIds, listingType)



                            const folderParts = activePlan.plan!.folder.split(/[\\/]/).filter((p: string) => p)
                            const dir = await ensureSubdirectory(dirHandle, folderParts)

                            debugCurrentFile = activePlan.plan!.filename
                            const result = await writeFileAtomic(dir, fixExt(activePlan.plan!.filename), new Blob([res.data]))
                            if (result.warning) console.warn(result.warning)

                            updateResult(key, activePlan.plan!.filename, 'success', undefined, result.warning, undefined)
                        } catch (e: any) {
                            console.error("Single write failed", e)
                            updateResult(key, activePlan.plan!.filename, 'failed', e.message || 'Write failed')
                        }
                    }
                } else {
                    throw new Error("No Save Plan available")
                }

                // Final Status Update
                const failureCount = currentResults.filter(r => r.status === 'failed').length

                // Trigger Image Warning Popup if any
                if (runValidationIssues.length > 0) {
                    setPostExportImageWarnings(runValidationIssues)
                }

                if (failureCount > 0) {
                    setFsStatus(`Completed with ${failureCount} errors.`)
                } else {
                    setFsStatus("All files saved successfully!")
                    setTimeout(() => setFsStatus(null), 5000)
                }

            } catch (err: any) {
                console.error(err)
                setError(`File System Error (at ${debugCurrentFile}): ` + (err.message || 'Unknown error'))
                setFsStatus(null)
            } finally {
                setDownloading(null)
            }
        } catch (err: any) {
            console.error(`[EXPORT][${format.toUpperCase()}] click: failed`, err);
            if (err instanceof DOMException) {
                console.error(`[EXPORT][${format.toUpperCase()}] DOMException`, { name: err.name, message: err.message });
            }
            throw err;
        }
    }

    const handleRunBothExports = async () => {
        if (selectedModels.size === 0) return
        setRunningBoth(true)
        setRunBothProgress('Initializing...')
        setError(null)

        try {
            // 1. Product Export
            setRunBothProgress('Downloading product export...')
            await triggerDownloadWithYield(async () => {
                if (productDefaultFormat === 'csv') {
                    await handleFileSystemDownload('csv')
                } else {
                    await handleFileSystemDownload('xlsx')
                }
            })

            // 2. Customization Export
            setRunBothProgress('Downloading customization export...')
            await triggerDownloadWithYield(async () => {
                if (customizationDefaultFormat === 'txt') {
                    console.warn('TXT run-both skipped (not supported independently)')
                } else {
                    await handleDownloadCustomizationXlsx()
                }
            })

        } catch (err: any) {
            console.error(err)
            setError('Run Both: Sequence failed. ' + (err.message || ''))
        } finally {
            setRunningBoth(false)
            setRunBothProgress('')
        }
    }

    const handleDownloadCustomizationXlsx = async () => {
        if (selectedModels.size === 0) return
        setLocalCustomizationFormat('xlsx')

        try {
            setDownloading('custom_xlsx')
            const response = await exportApi.downloadCustomizationXlsx(Array.from(selectedModels), listingType)

            const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
            const url = window.URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = url

            const contentDisposition = response.headers['content-disposition']
            let filename = `${buildAmazonExportFilenameBase(true)}.xlsx`
            if (contentDisposition) {
                const match = contentDisposition.match(/filename="?([^"]+)"?/)
                if (match && match[1]) filename = match[1]
            }

            link.setAttribute('download', filename)
            document.body.appendChild(link)
            link.click()
            link.parentNode?.removeChild(link)
            window.URL.revokeObjectURL(url)

        } catch (err) {
            console.error(err)
            const msg = await extractErrorMessage(err, 'Failed to download customization template.')
            setError(`Failed to download customization template: ${msg}`)
        } finally {
            setDownloading(null)
        }
    }

    const handleQuickCsvExport = () => {
        const fields: string[] = []
        if (quickCsvFields.asin) fields.push('ASIN')
        if (quickCsvFields.sku) fields.push('SKU')
        if (quickCsvFields.manufacturer) fields.push('Manufacturer')
        if (quickCsvFields.series) fields.push('Series')
        if (quickCsvFields.model) fields.push('Model')
        if (quickCsvFields.equipment_type) fields.push('Equipment Type')

        if (fields.length === 0 || selectedModels.size === 0) return

        const lines: string[] = []
        // Header Row
        if (includeHeaders) {
            const headerRow: string[] = []
            if (quickCsvFields.asin) headerRow.push(quickCsvHeaders.asin)
            if (quickCsvFields.sku) headerRow.push(quickCsvHeaders.sku)
            if (quickCsvFields.manufacturer) headerRow.push(quickCsvHeaders.manufacturer)
            if (quickCsvFields.series) headerRow.push(quickCsvHeaders.series)
            if (quickCsvFields.model) headerRow.push(quickCsvHeaders.model)
            if (quickCsvFields.equipment_type) headerRow.push(quickCsvHeaders.equipment_type)

            const escapedHeader = headerRow.map(val => {
                const s = String(val || '')
                if (s.includes('"') || s.includes(',') || s.includes('\n') || s.includes('\r')) {
                    return `"${s.replace(/"/g, '""')}"`
                }
                return s
            })
            lines.push(escapedHeader.join(','))
        }

        const modelsToExport = filteredModels.filter(m => selectedModels.has(m.id))

        modelsToExport.forEach(m => {
            const row: string[] = []

            if (quickCsvFields.asin) {
                const asin = m.marketplace_listings?.find(l => l.marketplace === 'amazon')?.external_id || ''
                row.push(asin)
            }
            if (quickCsvFields.sku) {
                row.push(m.parent_sku || '')
            }
            if (quickCsvFields.manufacturer) {
                const series = allSeries.find(s => s.id === m.series_id)
                const mfr = series ? manufacturers.find(mf => mf.id === series.manufacturer_id) : undefined
                row.push(mfr?.name || '')
            }
            if (quickCsvFields.series) {
                const series = allSeries.find(s => s.id === m.series_id)
                row.push(series?.name || '')
            }
            if (quickCsvFields.model) {
                row.push(m.name)
            }
            if (quickCsvFields.equipment_type) {
                const et = allEquipmentTypes.find(e => e.id === m.equipment_type_id)
                row.push(et?.name || '')
            }

            const escapedRow = row.map(val => {
                const s = String(val || '')
                if (s.includes('"') || s.includes(',') || s.includes('\n') || s.includes('\r')) {
                    return `"${s.replace(/"/g, '""')}"`
                }
                return s
            })
            lines.push(escapedRow.join(','))
        })

        const csvContent = lines.join('\n')
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', 'amazon_export_selection.csv')
        document.body.appendChild(link)
        link.click()
        setTimeout(() => {
            link.parentNode?.removeChild(link)
            URL.revokeObjectURL(url)
        }, 100)
    }

    const allSelected = filteredModels.length > 0 && filteredModels.every(m => selectedModels.has(m.id))
    const someSelected = filteredModels.some(m => selectedModels.has(m.id))



    if (loadError) {
        return (
            <Box sx={{ p: 4, display: 'flex', justifyContent: 'center' }}>
                <Paper sx={{ p: 4, maxWidth: 600, textAlign: 'center', borderColor: 'error.main', border: 1 }}>
                    <ErrorIcon color="error" sx={{ fontSize: 60, mb: 2 }} />
                    <Typography variant="h5" color="error" gutterBottom>
                        Initialization Failed
                    </Typography>
                    <Typography variant="body1" sx={{ mb: 2 }}>
                        The export page could not load required data.
                    </Typography>
                    <Box sx={{ mb: 3, p: 2, bgcolor: 'grey.100', borderRadius: 1, textAlign: 'left' }}>
                        <Typography variant="caption" display="block"><strong>Step:</strong> {loadStep}</Typography>
                        <Typography variant="caption" display="block" color="error"><strong>Error:</strong> {loadError}</Typography>
                    </Box>
                    <Button variant="contained" onClick={() => window.location.reload()}>
                        Reload Page
                    </Button>
                </Paper>
            </Box>
        )
    }

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400, flexDirection: 'column', gap: 2 }}>
                <CircularProgress />
                <Typography variant="body2" color="text.secondary">{loadStep}</Typography>
            </Box>
        )
    }

    return (
        <Box>
            <Typography variant="h4" gutterBottom>
                Amazon Export
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                Select models to generate an Amazon export worksheet. Models are automatically matched with templates based on their equipment type.
            </Typography>


            {/* Save Plan Display (disabled: downloads are browser-managed) */}
            {false && savePlan && (
                <Paper variant="outlined" sx={{ p: 2, mb: 3, bgcolor: '#f8f9fa' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="subtitle2" color="primary">
                            Settings: Proposed Save Plan
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {baseDir ? (
                                <>
                                    <Chip
                                        label={`Saving to: ${baseDir.name}`}
                                        icon={<FolderOpenIcon />}
                                        color="success"
                                        variant="outlined"
                                        onClick={() => pickBaseDirectory().then(h => setBaseDir(h))}
                                    />
                                    <Button
                                        size="small"
                                        variant="text"
                                        color="inherit"
                                        onClick={async () => {
                                            await clearPersistedHandle()
                                            setBaseDir(null)
                                        }}
                                    >
                                        Reset Saved Folder
                                    </Button>
                                </>
                            ) : (
                                <Button
                                    size="small"
                                    startIcon={<FolderOpenIcon />}
                                    onClick={() => pickBaseDirectory().then(h => setBaseDir(h))}
                                    variant="outlined"
                                >
                                    Choose Output Folder
                                </Button>
                            )}
                        </Box>
                    </Box>

                    {fsStatus && (
                        <Alert severity="info" sx={{ mb: 1 }}>{fsStatus}</Alert>
                    )}

                    {/* Write Summary */}
                    {writeResults.length > 0 && (
                        <Box sx={{ mt: 2, mb: 2, p: 2, bgcolor: '#fff', border: '1px solid #eee', borderRadius: 1 }}>
                            <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span>Export Summary ({writeResults.filter(r => r.status === 'success').length}/{writeResults.length} successful)</span>
                                <Button
                                    size="small"
                                    onClick={() => {
                                        setWriteResults([])
                                        setLastSavePlanSnapshot(null)
                                        setFsStatus(null)
                                        setPostExportImageWarnings([])

                                        // Clear Validation Cache on explicit clear
                                        setLastValidationKey(null)
                                        setLastValidationAtMs(null)
                                        setValidationReport(null)
                                    }}
                                >
                                    Clear
                                </Button>
                            </Typography>

                            {/* UI: Success List + Verification */}
                            <Box sx={{ maxHeight: 200, overflowY: 'auto', mb: 2 }}>
                                {writeResults.filter(r => r.status === 'success').map(r => (
                                    <Box key={r.key} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                        <CheckCircleIcon color="success" fontSize="small" />
                                        <Typography variant="caption" sx={{ flexGrow: 1 }}>
                                            {r.filename}
                                        </Typography>
                                        {r.warning && (
                                            <Typography variant="caption" color="warning.main">
                                                (Cleanup Warning: {r.warning})
                                            </Typography>
                                        )}
                                    </Box>
                                ))}
                            </Box>


                            {writeResults.filter(r => r.status === 'failed').length > 0 && (
                                <Box>
                                    <Alert severity="error" sx={{ mb: 1 }}>
                                        {writeResults.filter(r => r.status === 'failed').length} files failed to save.
                                    </Alert>
                                    <Box sx={{ maxHeight: 150, overflowY: 'auto', mb: 1 }}>
                                        {writeResults.filter(r => r.status === 'failed').map(r => (
                                            <Typography key={r.key} variant="caption" color="error" display="block">
                                                • {r.filename}: {r.errorMessage}
                                            </Typography>
                                        ))}
                                    </Box>
                                    <Button
                                        size="small"
                                        variant="contained"
                                        color="error"
                                        onClick={() => {
                                            handleFileSystemDownload('xlsx', true)
                                        }}
                                    >
                                        Retry Failed Files
                                    </Button>
                                    <Typography variant="caption" sx={{ ml: 1, color: 'text.secondary' }}>
                                        (Retries using XLSX as default)
                                    </Typography>
                                </Box>
                            )}
                        </Box>
                    )}

                    {savePlan ? (savePlan!.type === 'single' ? (
                        <Box>
                            <Typography variant="body2"><strong>Folder:</strong> {savePlan!.plan!.folder}</Typography>
                            <Typography variant="body2"><strong>File:</strong> {savePlan!.plan!.filename}</Typography>
                        </Box>
                    ) : (
                        <Box>
                            <Typography variant="body2" sx={{ mb: 1 }}><strong>Master File:</strong></Typography>
                            <Box sx={{ pl: 2, mb: 2, borderLeft: '2px solid #ddd' }}>
                                <Typography variant="body2">Folder: {savePlan!.master!.folder}</Typography>
                                <Typography variant="body2">File: {savePlan!.master!.filename}</Typography>
                            </Box>

                            <Typography variant="body2" sx={{ mb: 1 }}><strong>Per-Series Files ({savePlan!.children!.length}):</strong></Typography>
                            <Box sx={{ pl: 2, maxHeight: 100, overflowY: 'auto', borderLeft: '2px solid #ddd' }}>
                                {savePlan!.children?.map((child, i) => (
                                    <Box key={i} sx={{ mb: 1 }}>
                                        <Typography variant="caption" display="block">Folder: {child.folder}</Typography>
                                        <Typography variant="caption" display="block">File: {child.filename}</Typography>
                                    </Box>
                                ))}
                            </Box>
                        </Box>
                    )) : null}
                </Paper>
            )}

            {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                    <Typography component="div" sx={{ whiteSpace: 'pre-line' }}>
                        {error}
                    </Typography>
                </Alert>
            )}

            {missingSnapshots && (
                <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setMissingSnapshots(null)}>
                    <Typography variant="subtitle2">Missing Baseline Pricing Snapshots</Typography>
                    <Typography variant="body2">The following variants must be calculated before generating a preview:</Typography>
                    <Box sx={{ mt: 1, maxHeight: 200, overflow: 'auto' }}>
                        {Object.entries(missingSnapshots).map(([mid, variants]) => {
                            const model = allModels.find(m => m.id === Number(mid))
                            return (
                                <div key={mid}>
                                    <strong>{model?.name || `Model ${mid}`}</strong>: {variants.join(', ')}
                                </div>
                            )
                        })}
                    </Box>
                    <Button color="inherit" size="small" sx={{ mt: 1 }} onClick={handleRecalculateSelected} disabled={recalculating}>
                        {recalculating ? 'Fixing...' : 'Run Recalculate Now'}
                    </Button>
                </Alert>
            )}

            {/* Filter Models */}
            <Paper sx={{ p: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                    Filter Models
                </Typography>
                <Grid container spacing={2}>
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
                                    setSelectedSeries('')
                                    setSelectedModels(new Set())
                                    setMissingSnapshots(null)
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

                                        // Check if "All Series" was just selected
                                        const lastSelected = values[values.length - 1]

                                        if (lastSelected === ALL_SERIES_VALUE) {
                                            setSelectedSeriesValue(ALL_SERIES_VALUE)
                                            setSelectedSeriesIds([])
                                            setSelectedSeries('')
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
                                            setSelectedSeries('')
                                        } else {
                                            setSelectedSeriesValue(MULTI_SERIES_VALUE)
                                            setSelectedSeriesIds(resolvedSeriesIds)
                                            setSelectedSeries('') // Clear single generic series selector
                                        }
                                        // Missing snapshots will be recalculated or cleared by logic
                                        setMissingSnapshots(null)
                                    }}
                                    renderValue={(selected) => {
                                        if (selected.length === 0) {
                                            return <Typography color="text.secondary">Select series</Typography>
                                        }
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
                                        setSelectedSeries('')
                                        setSelectedModels(new Set())
                                        setMissingSnapshots(null)
                                        setValidationReport(null)
                                        setError(null)
                                }}
                                disabled={!selectedManufacturer && selectedModels.size === 0}
                            >
                                Clear
                            </Button>
                        </Box>
                    </Grid>
                    <Grid item xs={12} md={4}>
                        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', height: '100%' }}>
                            <Typography variant="body2" color="text.secondary">
                                {selectedModels.size} model{selectedModels.size !== 1 ? 's' : ''} selected
                            </Typography>
                            <Button
                                variant="outlined"
                                color="secondary"
                                size="small"
                                startIcon={<RefreshIcon />}
                                onClick={handleRecalculateSelected}
                                disabled={selectedModels.size === 0 || recalculating}
                            >
                                {recalculating ? 'Recalculating...' : 'Recalc Prices'}
                            </Button>

                            <Button
                                variant="outlined"
                                color="info"
                                size="small"
                                startIcon={<FactCheckIcon />}
                                onClick={handleValidateExport}
                                disabled={selectedModels.size === 0 || validating}
                            >
                                {validating ? 'Checking...' : 'Readiness Report'}
                            </Button>
                        </Box>
                    </Grid>
                </Grid>

                {/* Validation Report UI */}
                {validationReport && (
                    <Box sx={{ mt: 3, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1, bgcolor: '#fafafa' }}>
                        <Typography variant="subtitle1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            Export Readiness Report
                            {validationReport.status === 'valid' && <Chip label="Ready" color="success" size="small" icon={<CheckCircleIcon />} />}
                            {validationReport.status === 'warnings' && <Chip label="Warnings" color="warning" size="small" icon={<WarningIcon />} />}
                            {validationReport.status === 'errors' && <Chip label="Not Ready" color="error" size="small" icon={<ErrorIcon />} />}
                        </Typography>

                        <Box sx={{ display: 'flex', gap: 3, mb: 2 }}>
                            <Typography variant="body2"><strong>Models Checked:</strong> {validationReport.summary_counts.total_models}</Typography>
                            <Typography variant="body2" color="error.main"><strong>Errors:</strong> {validationReport.summary_counts.errors || 0}</Typography>
                            <Typography variant="body2" color="warning.main"><strong>Warnings:</strong> {validationReport.summary_counts.warnings || 0}</Typography>
                        </Box>

                        {validationReport.status === 'errors' && (
                            <Alert severity="error" sx={{ mb: 2 }}>
                                Critical issues found. Export is disabled until these are resolved.
                            </Alert>
                        )}

                        {validationReport.items.length > 0 ? (
                            <Box sx={{ maxHeight: 200, overflowY: 'auto', bgcolor: 'white', border: '1px solid #eee', p: 1 }}>
                                {validationReport.items.map((item, idx) => (
                                    <Box key={idx} sx={{ display: 'flex', gap: 1, mb: 0.5, alignItems: 'flex-start' }}>
                                        {item.severity === 'error' ? <ErrorIcon color="error" fontSize="small" sx={{ mt: 0.3 }} /> : <WarningIcon color="warning" fontSize="small" sx={{ mt: 0.3 }} />}
                                        <Box>
                                            <Typography variant="body2" color={item.severity === 'error' ? 'error' : 'text.primary'}>
                                                {item.model_name ? <strong>{item.model_name}: </strong> : ''}{item.message}
                                            </Typography>
                                        </Box>
                                    </Box>
                                ))}
                            </Box>
                        ) : (
                            <Typography variant="body2" color="text.secondary">No issues found.</Typography>
                        )}
                    </Box>
                )}

                <Box sx={{ mt: 3, pt: 2, borderTop: '1px solid #eee' }}>
                    <Typography variant="subtitle2" gutterBottom>
                        Listing Type
                    </Typography>
                    <ToggleButtonGroup
                        value={listingType}
                        exclusive
                        onChange={(_, value) => value && setListingType(value)}
                        size="small"
                    >
                        <ToggleButton value="individual">
                            <Tooltip title="Each model gets its own unique SKU in contribution_sku">
                                <span>Individual / Standard</span>
                            </Tooltip>
                        </ToggleButton>
                        <ToggleButton value="parent_child" disabled>
                            <Tooltip title="Parent/Child listing (Coming Soon)">
                                <span>Parent / Child</span>
                            </Tooltip>
                        </ToggleButton>
                    </ToggleButtonGroup>
                    <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                        {listingType === 'individual'
                            ? 'Each model will use its Parent SKU as the contribution_sku value'
                            : 'Parent/Child listing support coming soon'}
                    </Typography>
                </Box>
            </Paper>

            {/* Models Table (Accordion) */}
            <Accordion defaultExpanded={false} sx={{ mb: 3 }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Models ({selectedModels.size} selected)</Typography>
                </AccordionSummary>
                <AccordionDetails sx={{ p: 0 }}>
                    <Paper sx={{ p: 2, boxShadow: 'none' }}>
                        <Box sx={{ px: 1, py: 1, borderBottom: '1px solid #f0f0f0', mb: 1 }}>
                            <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                                {!selectedManufacturer
                                    ? "Select a manufacturer to view models."
                                    : selectedSeriesValue === ALL_SERIES_VALUE
                                        ? `Showing all models for ${manufacturers.find(m => m.id === selectedManufacturer)?.name || 'Manufacturer'} (all series)`
                                        : selectedSeriesIds.length === 0
                                            ? "Select one or more series to view models."
                                            : `Showing selected series for ${manufacturers.find(m => m.id === selectedManufacturer)?.name || 'Manufacturer'}`
                                }
                            </Typography>
                        </Box>
                        <TableContainer sx={{ maxHeight: 500 }}>
                            <Table stickyHeader size="small">
                                <TableHead>
                                    <TableRow>
                                        <TableCell padding="checkbox">
                                            <Checkbox
                                                checked={allSelected}
                                                indeterminate={someSelected && !allSelected}
                                                onChange={(e) => handleSelectAll(e.target.checked)}
                                            />
                                        </TableCell>
                                        <TableCell>Model</TableCell>
                                        <TableCell>Series</TableCell>
                                        <TableCell>Manufacturer</TableCell>
                                        <TableCell>Dimensions (W×D×H)</TableCell>
                                        <TableCell>Template</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {filteredModels.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={6} align="center">
                                                <Typography color="text.secondary">No models found</Typography>
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        filteredModels.map(model => {
                                            const templateCode = getTemplateForEquipmentType(model.equipment_type_id)
                                            return (
                                                <TableRow
                                                    key={model.id}
                                                    hover
                                                    selected={selectedModels.has(model.id)}
                                                >
                                                    <TableCell padding="checkbox">
                                                        <Checkbox
                                                            checked={selectedModels.has(model.id)}
                                                            onChange={(e) => handleSelectModel(model.id, e.target.checked)}
                                                        />
                                                    </TableCell>
                                                    <TableCell>{model.name}</TableCell>
                                                    <TableCell>{getSeriesName(model.series_id)}</TableCell>
                                                    <TableCell>{getManufacturerName(model.series_id)}</TableCell>
                                                    <TableCell>{model.width}" × {model.depth}" × {model.height}"</TableCell>
                                                    <TableCell>
                                                        {templateCode ? (
                                                            <Chip label={templateCode} size="small" color="primary" variant="outlined" />
                                                        ) : (
                                                            <Chip label="No template" size="small" color="warning" variant="outlined" />
                                                        )}
                                                    </TableCell>
                                                </TableRow>
                                            )
                                        })
                                    )}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    </Paper>
                </AccordionDetails>
            </Accordion>

            {/* Export Actions */}
            <Paper sx={{ p: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>Export Actions ({listingType === 'individual' ? 'Individual' : 'Parent/Child'})</Typography>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4, mb: 3 }}>
                    {/* Run Both Button */}
                    <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                        <Button
                            variant="contained"
                            color="secondary"
                            size="large"
                            onClick={handleRunBothExports}
                            disabled={selectedModels.size === 0 || downloading !== null || runningBoth}
                            startIcon={runningBoth ? <CircularProgress size={20} color="inherit" /> : <DownloadIcon />}
                            sx={{ px: 4, py: 1.5 }}
                        >
                            {runningBoth ? (runBothProgress || 'Running Exports...') : 'RUN BOTH EXPORTS'}
                        </Button>
                    </Box>

                    <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, alignItems: 'flex-start', justifyContent: 'center', gap: 6 }}>

                        {/* Customization Template Export */}
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Customization Template</Typography>
                            <Box sx={{ display: 'flex', gap: 2 }}>
                                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                    <Button
                                        variant={customizationDefaultFormat === 'txt' ? 'contained' : 'outlined'}
                                        size="small"
                                        startIcon={<DownloadIcon />}
                                        onClick={() => setCustomizationDefaultFormat('txt')}
                                    >
                                        TXT
                                    </Button>
                                    <Radio
                                        checked={customizationDefaultFormat === 'txt'}
                                        onChange={() => setCustomizationDefaultFormat('txt')}
                                        size="small"
                                    />
                                </Box>
                                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                    <Button
                                        variant={customizationDefaultFormat === 'xlsx' ? 'contained' : 'outlined'}
                                        size="small"
                                        startIcon={<DownloadIcon />}
                                        onClick={handleDownloadCustomizationXlsx}
                                        disabled={downloading !== null}
                                    >
                                        {downloading === 'custom_xlsx' ? 'Wait' : 'XLSX'}
                                    </Button>
                                    <Radio
                                        checked={customizationDefaultFormat === 'xlsx'}
                                        onChange={() => setCustomizationDefaultFormat('xlsx')}
                                        size="small"
                                    />
                                </Box>
                            </Box>
                        </Box>

                        <Divider orientation="vertical" flexItem sx={{ display: { xs: 'none', md: 'block' } }} />

                        {/* Product Template Export */}
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Product Template</Typography>
                            <Box sx={{ display: 'flex', gap: 2 }}>
                                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                    <Button
                                        variant="outlined"
                                        startIcon={<DownloadIcon />}
                                        onClick={() => handleFileSystemDownload('csv')}
                                        disabled={downloading !== null}
                                    >
                                        CSV
                                    </Button>
                                    <Radio
                                        checked={productDefaultFormat === 'csv'}
                                        onChange={() => setProductDefaultFormat('csv')}
                                        size="small"
                                    />
                                </Box>
                                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                    <Button
                                        variant="outlined"
                                        startIcon={<DownloadIcon />}
                                        onClick={() => handleFileSystemDownload('xlsx')}
                                        disabled={downloading !== null}
                                    >
                                        XLSX
                                    </Button>
                                    <Radio
                                        checked={productDefaultFormat === 'xlsx'}
                                        onChange={() => setProductDefaultFormat('xlsx')}
                                        size="small"
                                    />
                                </Box>
                            </Box>
                        </Box>

                    </Box>
                </Box>

                {/* Quick CSV Export */}
                <Box sx={{ mt: 4, pt: 2, borderTop: '1px solid #eee' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                        <Typography variant="subtitle2">Quick CSV Export</Typography>
                        <FormControlLabel
                            control={<Switch checked={includeHeaders} onChange={(e) => setIncludeHeaders(e.target.checked)} size="small" />}
                            label="Include Headers"
                        />
                    </Box>
                    <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 2, alignItems: 'start' }}>
                        {/* ASIN */}
                        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                            <FormControlLabel control={<Checkbox checked={quickCsvFields.asin} onChange={(e) => setQuickCsvFields({ ...quickCsvFields, asin: e.target.checked })} />} label="ASIN" />
                            <TextField
                                size="small"
                                value={quickCsvHeaders.asin}
                                onChange={(e) => setQuickCsvHeaders({ ...quickCsvHeaders, asin: e.target.value })}
                                disabled={!includeHeaders}
                                sx={{ mt: 0.5 }}
                            />
                        </Box>
                        {/* SKU */}
                        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                            <FormControlLabel control={<Checkbox checked={quickCsvFields.sku} onChange={(e) => setQuickCsvFields({ ...quickCsvFields, sku: e.target.checked })} />} label="SKU" />
                            <TextField
                                size="small"
                                value={quickCsvHeaders.sku}
                                onChange={(e) => setQuickCsvHeaders({ ...quickCsvHeaders, sku: e.target.value })}
                                disabled={!includeHeaders}
                                sx={{ mt: 0.5 }}
                            />
                        </Box>
                        {/* Manufacturer */}
                        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                            <FormControlLabel control={<Checkbox checked={quickCsvFields.manufacturer} onChange={(e) => setQuickCsvFields({ ...quickCsvFields, manufacturer: e.target.checked })} />} label="Manufacturer" />
                            <TextField
                                size="small"
                                value={quickCsvHeaders.manufacturer}
                                onChange={(e) => setQuickCsvHeaders({ ...quickCsvHeaders, manufacturer: e.target.value })}
                                disabled={!includeHeaders}
                                sx={{ mt: 0.5 }}
                            />
                        </Box>
                        {/* Series */}
                        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                            <FormControlLabel control={<Checkbox checked={quickCsvFields.series} onChange={(e) => setQuickCsvFields({ ...quickCsvFields, series: e.target.checked })} />} label="Series" />
                            <TextField
                                size="small"
                                value={quickCsvHeaders.series}
                                onChange={(e) => setQuickCsvHeaders({ ...quickCsvHeaders, series: e.target.value })}
                                disabled={!includeHeaders}
                                sx={{ mt: 0.5 }}
                            />
                        </Box>
                        {/* Model */}
                        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                            <FormControlLabel control={<Checkbox checked={quickCsvFields.model} onChange={(e) => setQuickCsvFields({ ...quickCsvFields, model: e.target.checked })} />} label="Model" />
                            <TextField
                                size="small"
                                value={quickCsvHeaders.model}
                                onChange={(e) => setQuickCsvHeaders({ ...quickCsvHeaders, model: e.target.value })}
                                disabled={!includeHeaders}
                                sx={{ mt: 0.5 }}
                            />
                        </Box>
                        {/* Equipment Type */}
                        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                            <FormControlLabel control={<Checkbox checked={quickCsvFields.equipment_type} onChange={(e) => setQuickCsvFields({ ...quickCsvFields, equipment_type: e.target.checked })} />} label="Equipment Type" />
                            <TextField
                                size="small"
                                value={quickCsvHeaders.equipment_type}
                                onChange={(e) => setQuickCsvHeaders({ ...quickCsvHeaders, equipment_type: e.target.value })}
                                disabled={!includeHeaders}
                                sx={{ mt: 0.5 }}
                            />
                        </Box>
                    </Box>

                    <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                        <Button
                            variant="contained"
                            onClick={handleQuickCsvExport}
                            disabled={selectedModels.size === 0 || !Object.values(quickCsvFields).some(Boolean)}
                            startIcon={<DownloadIcon />}
                        >
                            EXPORT
                        </Button>
                    </Box>
                </Box>

                {/* TXT Warning */}
                {includeCustomization && customizationDefaultFormat === 'txt' && (
                    <Alert
                        severity="warning"
                        sx={{ mt: 1, mb: 2 }}
                        action={
                            <Button
                                size="small"
                                onClick={async () => {
                                    const text =
                                        "To avoid blank TXT exports:\n" +
                                        "1) Open the customization template in Excel\n" +
                                        "2) Force recalculation (Ctrl+Alt+F9)\n" +
                                        "3) Save the file\n"

                                    try {
                                        await navigator.clipboard.writeText(text)
                                        setCustCopyCopied(true)
                                        window.setTimeout(() => setCustCopyCopied(false), 1500)
                                    } catch {
                                        // no-op
                                    }
                                }}
                            >
                                {custCopyCopied ? 'Copied!' : 'Copy steps'}
                            </Button>
                        }
                    >
                        <Stack spacing={0.5}>
                            <Typography variant="body2">
                                TXT generation uses cached values.
                            </Typography>
                        </Stack>
                    </Alert>
                )}

                {/* Missing Templates Warning (Full Width) */}
                {includeCustomization && missingTemplateNames.length > 0 && (
                    <Alert severity="error" sx={{ mt: 3 }}>
                        <Typography variant="subtitle2">Missing Default Customization Templates</Typography>
                        <Typography variant="body2" paragraph>
                            The following equipment types have no default template assigned:
                        </Typography>
                        <ul style={{ margin: '4px 0 12px 20px', padding: 0, fontSize: '0.875rem' }}>
                            {missingTemplateNames.map(name => <li key={name}>{name}</li>)}
                        </ul>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button component={RouterLink} to="/templates" size="small" variant="outlined">
                                Manage Templates
                            </Button>
                        </Box>
                    </Alert>
                )}

                {/* Path Settings (Collapsed) */}
                <Box sx={{ mt: 3, pt: 1, borderTop: '1px solid #eee' }}>
                    <Accordion elevation={0} sx={{ '&:before': { display: 'none' }, bgcolor: 'transparent' }}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 0 }}>
                            <Typography variant="caption" color="text.secondary">Advanced: Output Path Settings</Typography>
                        </AccordionSummary>
                        <AccordionDetails sx={{ px: 0 }}>
                            <Grid container spacing={2} alignItems="center">
                                <Grid item xs={12} md={9}>
                                    <TextField
                                        fullWidth
                                        label="Default Save Path Template"
                                        value={localSavePathTemplate}
                                        onChange={(e) => setLocalSavePathTemplate(e.target.value)}
                                        helperText="Supported: [Marketplace], [Manufacturer_Name], [Series_Name]"
                                        size="small"
                                    />
                                </Grid>
                                <Grid item xs={12} md={3}>
                                    <Button variant="outlined" onClick={handleSaveExportSettings} fullWidth>
                                        Save Path
                                    </Button>
                                </Grid>
                            </Grid>
                        </AccordionDetails>
                    </Accordion>
                </Box>
            </Paper>



            {/* Image Failure Warnings Popup */}
            <Dialog
                open={postExportImageWarnings.length > 0}
                onClose={() => setPostExportImageWarnings([])}
                maxWidth="md"
                fullWidth
            >
                <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'warning.main' }}>
                    <WarningIcon />
                    Export Completed with Image Warnings
                </DialogTitle>
                <DialogContent dividers>
                    <Alert severity="warning" sx={{ mb: 2 }}>
                        Some sampled image URLs were inaccessible or invalid. The export files were saved, but these images may be broken on Amazon.
                    </Alert>
                    <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 300 }}>
                        <Table size="small" stickyHeader>
                            <TableHead>
                                <TableRow>
                                    <TableCell>Model</TableCell>
                                    <TableCell>Issue</TableCell>
                                    <TableCell align="right">Action</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {postExportImageWarnings.map((issue, idx) => {
                                    // Extract URL if present in message "Image URL inaccessible (...): URL"
                                    const urlMatch = issue.message.match(/: (http.*)$/)
                                    const url = urlMatch ? urlMatch[1] : null
                                    return (
                                        <TableRow key={idx}>
                                            <TableCell>{issue.model_name || `ID ${issue.model_id}`}</TableCell>
                                            <TableCell sx={{ wordBreak: 'break-word', fontSize: '0.85rem' }}>
                                                {issue.message}
                                            </TableCell>
                                            <TableCell align="right">
                                                {url && (
                                                    <Tooltip title="Copy URL">
                                                        <IconButton size="small" onClick={() => navigator.clipboard.writeText(url)}>
                                                            <ContentCopyIcon fontSize="small" />
                                                        </IconButton>
                                                    </Tooltip>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    )
                                })}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setPostExportImageWarnings([])} color="primary" variant="contained">
                        Acknowledge
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}

