import { useEffect, useState, useMemo } from 'react'
import {
    Box, Typography, Paper, Button, Grid, FormControl, InputLabel, Select, MenuItem, CircularProgress, Alert, Chip,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Checkbox, TextField, Snackbar,
    Dialog, DialogTitle, DialogContent, DialogActions
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import {
    manufacturersApi, seriesApi, modelsApi, pricingApi, materialsApi, designOptionsApi,
    settingsApi, ebayVariationsApi, equipmentTypesApi, ebayExportApi, ebayVariationPresetsApi, ebayTemplatesApi,
    type GenerateVariationsResponse, type VariationRow, type EbayVariationPresetResponse, type TemplateFieldAssetResponse
} from '../services/api'
import type {
    Manufacturer, Series, Model, Material, MaterialColourSurcharge, DesignOption,
    MaterialRoleAssignment, MaterialRoleConfig, EquipmentType
} from '../types'

// Sentinel value for "All Series"
const ALL_SERIES_VALUE = '__ALL_SERIES__'
// Sentinel value for "Multi Series" mode (internal state usage)
const MULTI_SERIES_VALUE = '__MULTI__'

export default function EbayExportPage() {
    const [manufacturers, setManufacturers] = useState<Manufacturer[]>([])
    const [allSeries, setAllSeries] = useState<Series[]>([])
    const [allModels, setAllModels] = useState<Model[]>([])
    const [equipmentTypes, setEquipmentTypes] = useState<EquipmentType[]>([])

    const [selectedManufacturer, setSelectedManufacturer] = useState<number | ''>('')
    // selectedSeries (single) is deprecated for filtering, using multi-select ids instead
    const [selectedSeriesValue, setSelectedSeriesValue] = useState<string>('')
    const [selectedSeriesIds, setSelectedSeriesIds] = useState<number[]>([])
    const [selectedModels, setSelectedModels] = useState<Set<number>>(new Set())

    const [loading, setLoading] = useState(true)
    const [recalculating, setRecalculating] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Variation inputs state
    const [materials, setMaterials] = useState<Material[]>([])
    const [designOptions, setDesignOptions] = useState<DesignOption[]>([])
    const [selectedRoleKeys, setSelectedRoleKeys] = useState<string[]>([])
    const [selectedColourSurchargeIdsByRole, setSelectedColourSurchargeIdsByRole] = useState<Record<string, number[]>>({})
    const [selectedDesignOptionIds, setSelectedDesignOptionIds] = useState<number[]>([])
    const [materialRoles, setMaterialRoles] = useState<MaterialRoleAssignment[]>([])
    const [roleConfigs, setRoleConfigs] = useState<MaterialRoleConfig[]>([])

    // Variation generation state
    const [generatingVariations, setGeneratingVariations] = useState(false)
    const [variationError, setVariationError] = useState<string | null>(null)

    const [variationResult, setVariationResult] = useState<GenerateVariationsResponse | null>(null)
    const [loadingExisting, setLoadingExisting] = useState(false)
    const [exportingCsv, setExportingCsv] = useState(false)
    const [paddingMode, setPaddingMode] = useState<'both' | 'no_padding' | 'with_padding'>('both')

    // eBay Fabric Template settings state
    const [tplNoPad, setTplNoPad] = useState('')
    const [tplWithPad, setTplWithPad] = useState('')
    const [descriptionSelectionMode, setDescriptionSelectionMode] = useState<'GLOBAL_PRIMARY' | 'EQUIPMENT_TYPE_PRIMARY'>('GLOBAL_PRIMARY')
    const [settingsSnackbar, setSettingsSnackbar] = useState<{ message: string; severity: 'success' | 'error' } | null>(null)
    const [variationPresets, setVariationPresets] = useState<EbayVariationPresetResponse[]>([])
    const [savePresetOpen, setSavePresetOpen] = useState(false)
    const [savePresetName, setSavePresetName] = useState('')
    const [editingPresetId, setEditingPresetId] = useState<number | null>(null)
    const [assignPresetOpen, setAssignPresetOpen] = useState(false)
    const [assignPresetEntry, setAssignPresetEntry] = useState<EbayVariationPresetResponse | null>(null)
    const [assignEquipmentTypeIds, setAssignEquipmentTypeIds] = useState<number[]>([])
    const [assignError, setAssignError] = useState<string | null>(null)
    const [presetError, setPresetError] = useState<string | null>(null)
    const [presetSaving, setPresetSaving] = useState(false)
    const [descriptionAssets, setDescriptionAssets] = useState<TemplateFieldAssetResponse[]>([])
    const [descriptionAssetsLoading, setDescriptionAssetsLoading] = useState(false)

    // Existing variations viewer state

    const [existingVariations, setExistingVariations] = useState<VariationRow[]>([])

    // Load initial data
    useEffect(() => {
        loadData()
    }, [])

    const refreshVariationPresets = async () => {
        try {
            const rows = await ebayVariationPresetsApi.list()
            setVariationPresets(rows || [])
        } catch (err) {
            console.error('Failed to load variation presets', err)
        }
    }

    const refreshDescriptionAssets = async () => {
        try {
            setDescriptionAssetsLoading(true)
            const fieldsResp = await ebayTemplatesApi.getCurrentFields()
            const descriptionField = (fieldsResp.fields || []).find((field) =>
                field.field_name.replace(/\s+/g, '').replace(/_/g, '').toLowerCase() === 'description'
            )
            if (!descriptionField) {
                setDescriptionAssets([])
                return
            }
            const assets = await ebayTemplatesApi.getFieldAssets(descriptionField.id, 'description_html')
            setDescriptionAssets(assets || [])
        } catch (err) {
            console.error('Failed to load description assets', err)
            setDescriptionAssets([])
        } finally {
            setDescriptionAssetsLoading(false)
        }
    }

    const loadData = async () => {
        try {
            setLoading(true)
            const results = await Promise.allSettled([
                manufacturersApi.list(),
                seriesApi.list(),
                modelsApi.list(),
                materialsApi.list(),
                designOptionsApi.list(),
                settingsApi.listMaterialRoles(false), // Get active roles only
                settingsApi.listMaterialRoleConfigs(),
                equipmentTypesApi.list(),
                settingsApi.getExport()
            ])

            // Helper to safely extract results (TSX needs <T,> to avoid JSX parse confusion)
            const getResult = <T,>(index: number, defaultValue: T): T => {
                const res = results[index]
                if (res.status === 'fulfilled') {
                    return res.value as T
                }
                console.error(`Failed to load data at index ${index}:`, res.reason)
                return defaultValue
            }

            setManufacturers(getResult<Manufacturer[]>(0, []))
            setAllSeries(getResult<Series[]>(1, []))
            setAllModels(getResult<Model[]>(2, []))
            setMaterials(getResult<Material[]>(3, []))
            setDesignOptions(getResult<DesignOption[]>(4, []))
            setMaterialRoles(getResult<MaterialRoleAssignment[]>(5, []))
            setRoleConfigs(getResult<MaterialRoleConfig[]>(6, []))
            setEquipmentTypes(getResult<EquipmentType[]>(7, []))

            // Populate fabric template fields from export settings
            const exportResult = results[8]
            if (exportResult.status === 'fulfilled') {
                const exportData = exportResult.value as any
                setTplNoPad(exportData.ebay_fabric_template_no_padding ?? '')
                setTplWithPad(exportData.ebay_fabric_template_with_padding ?? '')
                setDescriptionSelectionMode(
                    exportData.ebay_description_selection_mode === 'EQUIPMENT_TYPE_PRIMARY'
                        ? 'EQUIPMENT_TYPE_PRIMARY'
                        : 'GLOBAL_PRIMARY'
                )
            }

            await refreshVariationPresets()
            await refreshDescriptionAssets()

        } catch (err: any) {
            setError(err.message || 'Failed to load data')
        } finally {
            setLoading(false)
        }
    }

    const handleSaveTemplateSettings = async () => {
        try {
            const result = await settingsApi.updateExport({
                ebay_fabric_template_no_padding: tplNoPad || null,
                ebay_fabric_template_with_padding: tplWithPad || null,
                ebay_description_selection_mode: descriptionSelectionMode,
            })
            setTplNoPad(result.ebay_fabric_template_no_padding ?? '')
            setTplWithPad(result.ebay_fabric_template_with_padding ?? '')
            setDescriptionSelectionMode(
                result.ebay_description_selection_mode === 'EQUIPMENT_TYPE_PRIMARY'
                    ? 'EQUIPMENT_TYPE_PRIMARY'
                    : 'GLOBAL_PRIMARY'
            )
            setSettingsSnackbar({ message: 'Export settings saved', severity: 'success' })
        } catch (err: any) {
            const detail = err?.response?.data?.detail || 'Failed to save export settings'
            setSettingsSnackbar({ message: detail, severity: 'error' })
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

    // Helper to normalize role key (ensure underscore format)
    const normalizeRoleKey = (role: string): string => {
        if (!role) return ''
        return role.toUpperCase().replace(/\s+/g, '_')
    }

    // Selectable roles (ebay_variation_enabled = true)
    const selectableRoles = useMemo(() => {
        return roleConfigs.filter(rc => rc.ebay_variation_enabled === true)
    }, [roleConfigs])

    // Helper to resolve active assignment for a role
    const resolveActiveAssignmentForRole = (roleKey: string) => {
        return materialRoles.find(mr =>
            normalizeRoleKey(mr.role) === roleKey &&
            (mr.end_date === null || mr.end_date === undefined || new Date(mr.end_date) > new Date())
        )
    }

    // Load surcharges for all selected roles
    const [surchargesByRole, setSurchargesByRole] = useState<Record<string, MaterialColourSurcharge[]>>({})

    useEffect(() => {
        const loadAllSurcharges = async () => {
            const newSurcharges: Record<string, MaterialColourSurcharge[]> = {}

            for (const roleKey of selectedRoleKeys) {
                const assignment = resolveActiveAssignmentForRole(roleKey)
                if (assignment?.material_id) {
                    try {
                        const surcharges = await materialsApi.listSurcharges(assignment.material_id)
                        newSurcharges[roleKey] = surcharges.filter(s => s.ebay_variation_enabled)
                    } catch (err) {
                        console.error(`Failed to load surcharges for role ${roleKey}:`, err)
                        newSurcharges[roleKey] = []
                    }
                }
            }

            setSurchargesByRole(newSurcharges)
        }

        if (selectedRoleKeys.length > 0) {
            loadAllSurcharges()
        } else {
            setSurchargesByRole({})
        }
    }, [selectedRoleKeys, materialRoles])

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
                if (m.exclude_from_ebay_export) reasons.push('Excluded from eBay export')

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

    // Filtered design options (only pricing relevant AND eBay variation enabled)
    const ebayDesignOptions = useMemo(() => {
        return designOptions
            .filter(opt => opt.is_pricing_relevant && opt.ebay_variation_enabled)
            .sort((a, b) => a.id - b.id) // Deterministic ordering by id
    }, [designOptions])

    useEffect(() => {
        if (designOptions.length > 0 && ebayDesignOptions.length === 0) {
            console.log('[EbayExportPage] designOptions fetched but eBay dropdown is empty', designOptions.map(opt => ({
                id: opt.id,
                name: opt.name,
                is_pricing_relevant: opt.is_pricing_relevant,
                ebay_variation_enabled: opt.ebay_variation_enabled,
            })))
        }
    }, [designOptions, ebayDesignOptions])

    const mapUiPaddingModeToPreset = (mode: 'both' | 'no_padding' | 'with_padding'): 'both' | 'non_padded' | 'padded' => {
        if (mode === 'no_padding') return 'non_padded'
        if (mode === 'with_padding') return 'padded'
        return 'both'
    }

    const mapPresetPaddingToUiMode = (mode: string): 'both' | 'no_padding' | 'with_padding' => {
        if (mode === 'non_padded') return 'no_padding'
        if (mode === 'padded') return 'with_padding'
        return 'both'
    }

    const buildPresetPayloadFromCurrentState = () => {
        const colorIds = Array.from(new Set(
            selectedRoleKeys.flatMap((roleKey) => selectedColourSurchargeIdsByRole[roleKey] || [])
        ))
        return {
            role_keys: [...selectedRoleKeys],
            color_surcharge_ids: colorIds,
            design_option_ids: [...selectedDesignOptionIds],
            with_padding: mapUiPaddingModeToPreset(paddingMode),
        }
    }

    const assignedPresets = useMemo(
        () => variationPresets.filter((preset) => (preset.equipment_type_ids || []).length > 0),
        [variationPresets]
    )
    const unassignedPresets = useMemo(
        () => variationPresets.filter((preset) => (preset.equipment_type_ids || []).length === 0),
        [variationPresets]
    )

    const descriptionPreflight = useMemo(() => {
        if (selectedModels.size === 0) {
            return { canExport: true, severity: null as null | 'info' | 'warning' | 'error', message: '' }
        }
        if (descriptionAssetsLoading) {
            return { canExport: false, severity: 'info' as const, message: 'Checking description template resolution…' }
        }

        const selectedModelRows = Array.from(selectedModels)
            .map((id) => allModels.find((m) => m.id === id))
            .filter((m): m is Model => Boolean(m))

        const usableGlobalAssets = descriptionAssets
            .filter((asset) => asset.is_default_fallback === true && (asset.value || '').trim().length > 0)
            .sort((a, b) => b.id - a.id)
        const globalAsset = usableGlobalAssets[0] || null

        const resolvedByModel = selectedModelRows.map((model) => {
            const equipmentTypeId = model.equipment_type_id
            const usableSpecificAssets = descriptionAssets
                .filter((asset) =>
                    asset.is_default_fallback !== true &&
                    (asset.equipment_type_ids || []).includes(equipmentTypeId) &&
                    (asset.value || '').trim().length > 0
                )
                .sort((a, b) => b.id - a.id)
            const specificAsset = usableSpecificAssets[0] || null

            const resolved = descriptionSelectionMode === 'EQUIPMENT_TYPE_PRIMARY'
                ? (specificAsset || globalAsset)
                : (globalAsset || specificAsset)
            return { model, asset: resolved }
        })

        const unresolvedModels = resolvedByModel.filter((row) => !row.asset)
        if (unresolvedModels.length > 0) {
            return {
                canExport: false,
                severity: 'error' as const,
                message: 'No description template found for one or more models.',
            }
        }

        const uniqueAssets = new Map<number, TemplateFieldAssetResponse>()
        for (const row of resolvedByModel) {
            if (row.asset) uniqueAssets.set(row.asset.id, row.asset)
        }
        if (uniqueAssets.size > 1) {
            const assetNames = Array.from(uniqueAssets.values()).map((asset) =>
                (asset.name || '').trim() || `Asset ${asset.id}`
            )
            return {
                canExport: false,
                severity: 'warning' as const,
                message:
                    'Selected models use multiple description templates. Please export models that share the same description template. ' +
                    assetNames.join(', '),
            }
        }

        const singleAsset = Array.from(uniqueAssets.values())[0]
        const singleName = singleAsset ? ((singleAsset.name || '').trim() || `Asset ${singleAsset.id}`) : ''
        return {
            canExport: true,
            severity: 'info' as const,
            message: `Using description template: ${singleName}`,
        }
    }, [selectedModels, allModels, descriptionAssets, descriptionAssetsLoading, descriptionSelectionMode])

    // Handle role change - manage color selections
    const handleRoleChange = (roleKeys: string[]) => {
        setSelectedRoleKeys(roleKeys)

        // Clean up color selections for removed roles
        const newColorSelections: Record<string, number[]> = {}
        for (const roleKey of roleKeys) {
            newColorSelections[roleKey] = selectedColourSurchargeIdsByRole[roleKey] || []
        }
        setSelectedColourSurchargeIdsByRole(newColorSelections)
    }

    // Helper to format abbreviations (1-3 chars valid)
    const formatAbbrev = (abbrev?: string | null): string => {
        const trimmed = abbrev?.trim()
        if (!trimmed) return '(missing)'
        if (trimmed.length > 3) return `${trimmed} (invalid; max 3)`
        return trimmed
    }

    // Helper to format role SKU pair
    const formatRoleSkuPair = (noPad?: string | null, withPad?: string | null): string => {
        const validNoPad = noPad?.trim() && noPad.trim().length >= 1 && noPad.trim().length <= 3 ? noPad.trim() : null
        const validWithPad = withPad?.trim() && withPad.trim().length >= 1 && withPad.trim().length <= 3 ? withPad.trim() : null

        if (validNoPad && validWithPad && validNoPad !== validWithPad) {
            return `${validNoPad}, ${validWithPad}`
        }
        if (validNoPad) return validNoPad
        if (validWithPad) return validWithPad
        return '(missing)'
    }

    // Helper functions to format IDs into human-readable display
    const formatMaterialDisplay = (materialId: number): string => {
        const material = materials.find(m => m.id === materialId)
        if (!material) return `Material ${materialId}`
        const abbrev = material.sku_abbreviation ? ` (${material.sku_abbreviation})` : ''
        return `${material.name}${abbrev}`
    }

    const formatColorDisplay = (colorId: number | null, roleColorsList: MaterialColourSurcharge[]): string => {
        if (!colorId) return '-'
        const color = roleColorsList.find(c => c.id === colorId)
        if (!color) return `Color ${colorId}`
        const abbrev = color.sku_abbreviation ? ` (${color.sku_abbreviation})` : ''
        return `${color.colour}${abbrev}`
    }

    const formatDesignOptionsDisplay = (optionIds: number[]): string => {
        if (!optionIds || optionIds.length === 0) return '-'
        return optionIds.map(id => {
            const opt = designOptions.find(o => o.id === id)
            if (!opt) return `ID ${id}`
            const abbrev = opt.sku_abbreviation ? ` (${opt.sku_abbreviation})` : ''
            return `${opt.name}${abbrev}`
        }).join(', ')
    }

    const formatPresetEquipmentTypes = (equipmentTypeIds: number[]): string => {
        if (!equipmentTypeIds || equipmentTypeIds.length === 0) return '(none)'
        return equipmentTypeIds
            .map((id) => equipmentTypes.find((et) => et.id === id)?.name || `ID ${id}`)
            .join(', ')
    }

    // Handle load existing variations
    const handleLoadExisting = async () => {
        if (selectedModels.size === 0) return

        setLoadingExisting(true)
        setExistingVariations([])

        try {
            const modelIds = Array.from(selectedModels)
            const variations = await ebayVariationsApi.getExisting(modelIds)
            setExistingVariations(variations)
        } catch (err: any) {
            console.error('Failed to load existing variations:', err)
        } finally {
            setLoadingExisting(false)
        }
    }

    const handleGenerateVariations = async () => {
        setVariationError(null)
        setVariationResult(null)
        setGeneratingVariations(true)

        try {
            // Deterministic ordering
            const roleKeysSorted = [...selectedRoleKeys].sort()
            const modelIds = Array.from(selectedModels)

            let totalCreated = 0
            let totalUpdated = 0
            const allRows: VariationRow[] = []

            // Generate for each role × color combination
            for (const roleKey of roleKeysSorted) {
                const colorIds = selectedColourSurchargeIdsByRole[roleKey] || []
                const colorIdsSorted = [...new Set(colorIds)].sort((a, b) => a - b)

                for (const colorId of colorIdsSorted) {
                    const payload = {
                        model_ids: modelIds,
                        role_key: roleKey, // Already normalized
                        material_colour_surcharge_id: colorId,
                        design_option_ids: selectedDesignOptionIds,
                        pricing_option_ids: [],
                        use_variation_presets: true,
                    }

                    console.log('Generate Variations Payload:', payload)

                    const result = await ebayVariationsApi.generate(payload)
                    totalCreated += result.created
                    totalUpdated += result.updated
                    allRows.push(...result.rows)
                }
            }

            // Deduplicate by SKU (in case of overlaps)
            const uniqueRows = Array.from(
                new Map(allRows.map(row => [row.sku, row])).values()
            )

            setVariationResult({
                created: totalCreated,
                updated: totalUpdated,
                errors: [],
                rows: uniqueRows
            })
        } catch (err: any) {
            if (handlePresetExportError(err)) {
                return
            }
            // Handle structured error detail from backend
            const detail = err.response?.data?.detail

            if (typeof detail === 'object' && detail !== null) {
                // Structured error with invalid IDs
                let errorMsg = detail.message || 'Validation failed'
                const errorParts: string[] = [errorMsg]

                if (detail.missing_role_config_abbrev_no_padding) {
                    errorParts.push(`• Missing role config abbreviation (no padding) for role: ${detail.missing_role_config_abbrev_no_padding}`)
                }
                if (detail.missing_role_config_abbrev_with_padding) {
                    errorParts.push(`• Missing role config abbreviation (with padding) for role: ${detail.missing_role_config_abbrev_with_padding}`)
                }
                if (detail.invalid_material_id) {
                    errorParts.push(`• Invalid material ID: ${detail.invalid_material_id}`)
                }
                if (detail.invalid_color_id) {
                    errorParts.push(`• Invalid color ID: ${detail.invalid_color_id}`)
                }
                if (detail.invalid_design_option_ids && detail.invalid_design_option_ids.length > 0) {
                    errorParts.push(`• Invalid design option IDs: ${detail.invalid_design_option_ids.join(', ')}`)
                }

                setVariationError(errorParts.join('\n'))
            } else {
                // Fallback to string error
                const errorMessage = detail || err.message || 'Failed to generate variations'
                setVariationError(errorMessage)
            }
        } finally {
            setGeneratingVariations(false)
        }
    }

    // Generate Base Variants (C, CG, L, LG) with specific ordering
    const handleGenerateBaseVariants = async () => {
        setVariationError(null)
        setVariationResult(null)
        setGeneratingVariations(true)

        // Validation: Ensure every selected role has at least one color selected
        const unconfiguredRoles = selectedRoleKeys.filter(roleKey => {
            const colors = selectedColourSurchargeIdsByRole[roleKey] || []
            return colors.length === 0
        })

        if (unconfiguredRoles.length > 0) {
            const roleNames = unconfiguredRoles.map(key => {
                const cfg = roleConfigs.find(c => normalizeRoleKey(c.role) === key)
                return cfg?.display_name || key // Fallback to key if label missing
            }).join(', ')
            setVariationError(`Please select at least one color for the following roles: ${roleNames}`)
            return
        }

        setGeneratingVariations(true)
        setVariationError(null)

        try {
            const modelIds = Array.from(selectedModels)
            let totalCreated = 0
            let totalUpdated = 0
            const allRows: VariationRow[] = []

            for (const roleKey of selectedRoleKeys) {
                const config = roleConfigs.find(c => normalizeRoleKey(c.role) === roleKey)
                const colorIds = selectedColourSurchargeIdsByRole[roleKey] || []

                // Get color objects for sorting
                const selectedColors = (surchargesByRole[roleKey] || [])
                    .filter(s => colorIds.includes(s.id))

                // Sort colors: PBK first, then alphabetical by colour name
                selectedColors.sort((a, b) => {
                    const aIsPbk = a.colour === 'PBK'
                    const bIsPbk = b.colour === 'PBK'
                    if (aIsPbk && !bIsPbk) return -1
                    if (!aIsPbk && bIsPbk) return 1
                    return a.colour.localeCompare(b.colour)
                })

                // Determine padding configurations
                // Use settings based on valid abbreviation availability
                const canNoPad = !!(config?.sku_abbrev_no_padding && config.sku_abbrev_no_padding.trim().length > 0 && config.sku_abbrev_no_padding.trim().length <= 3)
                const canWithPad = !!(config?.sku_abbrev_with_padding && config.sku_abbrev_with_padding.trim().length > 0 && config.sku_abbrev_with_padding.trim().length <= 3)

                const paddingConfigs: boolean[] = []
                // Priority: No Pad, then With Pad
                if (canNoPad) paddingConfigs.push(false)
                if (canWithPad) paddingConfigs.push(true)

                // Sort design options
                // We generated them based on sorted `ebayDesignOptions`. 
                // However, the selected list is just IDs. We should sort them to ensure deterministic key generation if array order matters backend (it usually sorts, but safe to be consistent)
                const sortedDesignOptionIds = [...selectedDesignOptionIds].sort((a, b) => a - b)

                if (paddingConfigs.length === 0) {
                    console.warn(`Role ${roleKey} has no valid padding abbreviations configured. Skipping.`)
                    continue
                }

                for (const withPadding of paddingConfigs) {
                    for (const color of selectedColors) {

                        // 1. Always generate baseline with NO design options
                        const payloadBaseline = {
                            model_ids: modelIds,
                            role_key: roleKey,
                            material_colour_surcharge_id: color.id,
                            design_option_ids: [], // Empty for baseline
                            pricing_option_ids: [],
                            with_padding: withPadding,
                            use_variation_presets: true,
                        }

                        try {
                            const result = await ebayVariationsApi.generate(payloadBaseline)
                            totalCreated += result.created
                            totalUpdated += result.updated
                            allRows.push(...result.rows)
                        } catch (innerErr) {
                            console.error("Baseline variant generation failed", innerErr)
                            throw innerErr
                        }

                        // 2. If design options are selected, generate that variation too
                        if (sortedDesignOptionIds.length > 0) {
                            const payloadOptions = {
                                model_ids: modelIds,
                                role_key: roleKey,
                                material_colour_surcharge_id: color.id,
                                design_option_ids: sortedDesignOptionIds,
                                pricing_option_ids: [],
                                with_padding: withPadding,
                                use_variation_presets: true,
                            }

                            try {
                                const result = await ebayVariationsApi.generate(payloadOptions)
                                totalCreated += result.created
                                totalUpdated += result.updated
                                allRows.push(...result.rows)
                            } catch (innerErr) {
                                console.error("Options variant generation failed", innerErr)
                                throw innerErr
                            }
                        }
                    }
                }
            }

            setVariationResult({
                created: totalCreated,
                updated: totalUpdated,
                errors: [],
                rows: allRows // This might be massive, maybe just last batch? Or accumulated. 
                // The API returns rows for the batch. We accumulated them.
                // Ideally we should re-fetch all for these models to be sure we see everything.
            })

            // Refresh existing variations list to show everything
            await handleLoadExisting()

        } catch (err: any) {
            console.error(err)
            if (handlePresetExportError(err)) {
                return
            }
            setVariationError(err.message || 'Failed to generate variants')
        } finally {
            setGeneratingVariations(false)
        }
    }

    const handleOpenCreatePreset = () => {
        setEditingPresetId(null)
        setSavePresetName('')
        setPresetError(null)
        setSavePresetOpen(true)
    }

    const handleOpenEditPreset = async (entry: EbayVariationPresetResponse) => {
        const loaded = await handleLoadPreset(entry)
        if (!loaded) return
        setEditingPresetId(entry.id)
        setSavePresetName(entry.name || '')
        setPresetError(null)
        setSavePresetOpen(true)
    }

    const handleSavePreset = async () => {
        const trimmedName = savePresetName.trim()
        if (!trimmedName) return

        try {
            setPresetSaving(true)
            setPresetError(null)
            const payload = buildPresetPayloadFromCurrentState()

            if (editingPresetId) {
                await ebayVariationPresetsApi.update(editingPresetId, {
                    name: trimmedName,
                    payload,
                })
                setSettingsSnackbar({ message: 'Preset updated', severity: 'success' })
            } else {
                await ebayVariationPresetsApi.create({
                    name: trimmedName,
                    equipment_type_ids: [],
                    payload,
                })
                setSettingsSnackbar({ message: 'Preset saved', severity: 'success' })
            }

            setSavePresetOpen(false)
            setSavePresetName('')
            setEditingPresetId(null)
            await refreshVariationPresets()
        } catch (err: any) {
            const detail = err?.response?.data?.detail
            setPresetError(typeof detail === 'string' ? detail : 'Failed to save preset')
        } finally {
            setPresetSaving(false)
        }
    }

    const handleDeletePreset = async (entry: EbayVariationPresetResponse) => {
        const ok = window.confirm(`Delete preset "${entry.name}"?`)
        if (!ok) return
        try {
            await ebayVariationPresetsApi.remove(entry.id)
            await refreshVariationPresets()
            setSettingsSnackbar({ message: 'Preset deleted', severity: 'success' })
        } catch (err) {
            console.error('Failed to delete preset', err)
            setSettingsSnackbar({ message: 'Failed to delete preset', severity: 'error' })
        }
    }

    const handleOpenAssignPreset = (entry: EbayVariationPresetResponse) => {
        setAssignPresetEntry(entry)
        setAssignEquipmentTypeIds([...(entry.equipment_type_ids || [])])
        setAssignError(null)
        setAssignPresetOpen(true)
    }

    const handleSavePresetAssignments = async () => {
        if (!assignPresetEntry) return
        try {
            await ebayVariationPresetsApi.update(assignPresetEntry.id, {
                equipment_type_ids: [...assignEquipmentTypeIds],
            })
            setAssignPresetOpen(false)
            setAssignPresetEntry(null)
            setAssignEquipmentTypeIds([])
            setAssignError(null)
            await refreshVariationPresets()
            setSettingsSnackbar({ message: 'Preset assignments updated', severity: 'success' })
        } catch (err) {
            console.error('Failed to update preset assignments', err)
            setAssignError('Failed to save assignments')
        }
    }

    const handleLoadPreset = async (entry: EbayVariationPresetResponse): Promise<boolean> => {
        const payload = entry.payload
        if (!payload) {
            setPresetError('Preset payload is missing')
            return false
        }

        const availableRoleKeys = new Set(selectableRoles.map((rc) => normalizeRoleKey(rc.role)))
        const missingRoleKeys = payload.role_keys.filter((roleKey) => !availableRoleKeys.has(roleKey))
        if (missingRoleKeys.length > 0) {
            setPresetError(`Preset contains role keys not available in current catalog: ${missingRoleKeys.join(', ')}`)
            return false
        }

        const surchargesForPresetRoles: Record<string, MaterialColourSurcharge[]> = {}
        for (const roleKey of payload.role_keys) {
            const assignment = resolveActiveAssignmentForRole(roleKey)
            if (!assignment?.material_id) {
                setPresetError(`Preset role ${roleKey} has no active material assignment`)
                return false
            }
            try {
                const surcharges = await materialsApi.listSurcharges(assignment.material_id)
                surchargesForPresetRoles[roleKey] = surcharges.filter((s) => s.ebay_variation_enabled)
            } catch {
                setPresetError(`Failed to load colors for preset role ${roleKey}`)
                return false
            }
        }

        const availableColorIdSet = new Set(
            Object.values(surchargesForPresetRoles).flat().map((surcharge) => surcharge.id)
        )
        const missingColorIds = payload.color_surcharge_ids.filter((colorId) => !availableColorIdSet.has(colorId))
        if (missingColorIds.length > 0) {
            setPresetError(`Preset contains color_surcharge_id values not available in current catalog: ${missingColorIds.join(', ')}`)
            return false
        }

        const availableDesignOptionIdSet = new Set(ebayDesignOptions.map((opt) => opt.id))
        const missingDesignOptionIds = payload.design_option_ids.filter((id) => !availableDesignOptionIdSet.has(id))
        if (missingDesignOptionIds.length > 0) {
            setPresetError(`Preset contains design_option_id values not available in current catalog: ${missingDesignOptionIds.join(', ')}`)
            return false
        }

        const nextColorsByRole: Record<string, number[]> = {}
        for (const roleKey of payload.role_keys) {
            const roleColorIdSet = new Set((surchargesForPresetRoles[roleKey] || []).map((s) => s.id))
            nextColorsByRole[roleKey] = payload.color_surcharge_ids.filter((colorId) => roleColorIdSet.has(colorId))
        }

        setSelectedRoleKeys([...payload.role_keys])
        setSelectedColourSurchargeIdsByRole(nextColorsByRole)
        setSelectedDesignOptionIds([...payload.design_option_ids])
        setPaddingMode(mapPresetPaddingToUiMode(payload.with_padding))
        setSurchargesByRole(surchargesForPresetRoles)
        setPresetError(null)
        setSettingsSnackbar({ message: `Preset loaded: ${entry.name}`, severity: 'success' })
        return true
    }

    const handlePresetExportError = (err: any): boolean => {
        const code = err?.response?.data?.detail?.code
        if (code === 'variation_preset_missing_for_equipment_type') {
            setSettingsSnackbar({ message: 'No variation preset assigned for this equipment type.', severity: 'error' })
            return true
        }
        if (code === 'variation_preset_ambiguous_for_equipment_type') {
            setSettingsSnackbar({
                message: 'Multiple variation presets assigned to this equipment type. Please fix preset assignments.',
                severity: 'error'
            })
            return true
        }
        return false
    }


    const handleExportCsv = async () => {
        try {
            setExportingCsv(true)

            // Build payload
            const modelIds = Array.from(selectedModels)

            // Collect all selected color IDs across all roles
            const allColorIds: number[] = []
            for (const roleKey of selectedRoleKeys) {
                const colors = selectedColourSurchargeIdsByRole[roleKey] || []
                allColorIds.push(...colors)
            }

            // Check if we have active selections (Selection-Driven Mode)
            const hasSelections = selectedRoleKeys.length > 0 || allColorIds.length > 0 || selectedDesignOptionIds.length > 0

            const payload: any = {
                model_ids: modelIds,
                with_padding: paddingMode,
                use_variation_presets: true,
            }

            if (hasSelections) {
                payload.export_mode = 'selection_driven'
                payload.role_keys = selectedRoleKeys
                payload.color_surcharge_ids = allColorIds
                payload.design_option_ids = selectedDesignOptionIds
            }

            console.log("EBAY EXPORT PAYLOAD", payload)
            const response = await ebayExportApi.exportCsv(payload)

            // Create blob link to download
            const url = window.URL.createObjectURL(new Blob([response.data]))
            const link = document.createElement('a')
            link.href = url
            let filename = 'ebay_export.csv'
            const disposition = response.headers?.['content-disposition']
            if (typeof disposition === 'string' && disposition.includes('attachment')) {
                const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
                const matches = filenameRegex.exec(disposition)
                if (matches && matches[1]) {
                    filename = matches[1].replace(/['"]/g, '')
                }
            }
            link.setAttribute('download', filename)
            document.body.appendChild(link)
            link.click()
            link.remove() // Clean up
        } catch (err: any) {
            console.error('Export failed', err)
            if (handlePresetExportError(err)) {
                return
            }
            alert(`Export failed: ${err.message}`)
        } finally {
            setExportingCsv(false)
        }
    }

    const isGenerateEnabled = useMemo(() => {
        if (selectedModels.size === 0) return false
        if (selectedRoleKeys.length === 0) return false

        // Check that every selected role has at least one color
        for (const roleKey of selectedRoleKeys) {
            const colors = selectedColourSurchargeIdsByRole[roleKey] || []
            if (colors.length === 0) return false
        }

        return true
    }, [selectedModels, selectedRoleKeys, selectedColourSurchargeIdsByRole])

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
                <CircularProgress />
            </Box>
        )
    }

    return (
        <Box>
            <Typography variant="h4" gutterBottom>eBay Export</Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
                Select models to prepare for eBay export. Export functionality coming soon.
            </Typography>

            {error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                    <Typography component="div" sx={{ whiteSpace: 'pre-line' }}>
                        {error}
                    </Typography>
                </Alert>
            )}

            <Paper sx={{ p: 2, mt: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>eBay Export Settings</Typography>
                <Grid container spacing={2} alignItems="flex-start">
                    <Grid item xs={12} md={5}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Fabric Template (Non-padded)"
                            value={tplNoPad}
                            onChange={e => setTplNoPad(e.target.value)}
                            helperText='Must include {role}'
                            placeholder="{role}"
                        />
                    </Grid>
                    <Grid item xs={12} md={5}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Fabric Template (Padded)"
                            value={tplWithPad}
                            onChange={e => setTplWithPad(e.target.value)}
                            helperText='Must include {role}'
                            placeholder="{role} w/ Padding"
                        />
                    </Grid>
                    <Grid item xs={12} md={5}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Description selection mode</InputLabel>
                            <Select
                                value={descriptionSelectionMode}
                                label="Description selection mode"
                                onChange={(e) => setDescriptionSelectionMode(e.target.value as 'GLOBAL_PRIMARY' | 'EQUIPMENT_TYPE_PRIMARY')}
                            >
                                <MenuItem value="GLOBAL_PRIMARY">GLOBAL_PRIMARY</MenuItem>
                                <MenuItem value="EQUIPMENT_TYPE_PRIMARY">EQUIPMENT_TYPE_PRIMARY</MenuItem>
                            </Select>
                        </FormControl>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                            {descriptionSelectionMode === 'EQUIPMENT_TYPE_PRIMARY'
                                ? 'Use equipment-type description when assigned; otherwise use Global.'
                                : 'Use Global description when present; otherwise use equipment-type description.'}
                        </Typography>
                    </Grid>
                    <Grid item xs={12} md={2} sx={{ display: 'flex', alignItems: 'center', pt: 1 }}>
                        <Button variant="contained" size="small" onClick={handleSaveTemplateSettings}>Save</Button>
                    </Grid>
                </Grid>
                <Snackbar
                    open={!!settingsSnackbar}
                    autoHideDuration={4000}
                    onClose={() => setSettingsSnackbar(null)}
                >
                    {settingsSnackbar ? (
                        <Alert onClose={() => setSettingsSnackbar(null)} severity={settingsSnackbar.severity} sx={{ width: '100%' }}>
                            {settingsSnackbar.message}
                        </Alert>
                    ) : <div />}
                </Snackbar>
            </Paper>

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

            {/* Models to Export Section */}
            <Paper sx={{ p: 3, mt: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">Models to Export</Typography>
                    {selectedManufacturer && (
                        <Typography variant="body2" color="text.secondary">
                            Showing {filteredModels.length} models • {selectedModels.size} selected
                        </Typography>
                    )}
                </Box>

                {!selectedManufacturer ? (
                    <Alert severity="info">Select a manufacturer to view models.</Alert>
                ) : (
                    <TableContainer sx={{ maxHeight: 400 }}>
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
                                    <TableCell>Dimensions (W x D x H)</TableCell>
                                    <TableCell>Equipment Type</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {filteredModels.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} align="center" sx={{ py: 3 }}>
                                            <Typography variant="body2" color="text.secondary">
                                                No models found matching the filters.
                                            </Typography>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredModels.map((model) => {
                                        const isSelected = selectedModels.has(model.id)
                                        const series = allSeries.find(s => s.id === model.series_id)
                                        const eqType = equipmentTypes.find(et => et.id === model.equipment_type_id)

                                        return (
                                            <TableRow
                                                key={model.id}
                                                hover
                                                selected={isSelected}
                                                onClick={() => {
                                                    const newSelected = new Set(selectedModels)
                                                    if (newSelected.has(model.id)) {
                                                        newSelected.delete(model.id)
                                                    } else {
                                                        newSelected.add(model.id)
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
                                                            if (newSelected.has(model.id)) {
                                                                newSelected.delete(model.id)
                                                            } else {
                                                                newSelected.add(model.id)
                                                            }
                                                            setSelectedModels(newSelected)
                                                        }}
                                                    />
                                                </TableCell>
                                                <TableCell>{model.name}</TableCell>
                                                <TableCell>{series?.name || '-'}</TableCell>
                                                <TableCell>{`${model.width || '-'} " x ${model.depth || '-'} " x ${model.height || '-'} "`}</TableCell>
                                                <TableCell>{eqType?.name || '-'}</TableCell>
                                            </TableRow>
                                        )
                                    })
                                )}
                            </TableBody>
                        </Table>
                    </TableContainer>
                )}
            </Paper>

            {/* Variation Inputs Section */}
            <Paper sx={{ p: 3, mt: 3 }}>
                <Alert severity="info" sx={{ mb: 2 }}>
                    Variation presets will be used automatically based on equipment type.
                </Alert>
                {descriptionPreflight.message ? (
                    <Alert severity={descriptionPreflight.severity || 'info'} sx={{ mb: 2 }}>
                        {descriptionPreflight.message}
                    </Alert>
                ) : null}
                <Typography variant="h6" gutterBottom>Variation Inputs</Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                    Select material roles, colors per role, and design options for eBay variation SKU generation.
                </Typography>

                <Grid container spacing={2} sx={{ mt: 2 }}>
                    <Grid item xs={12}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Material Roles</InputLabel>
                            <Select
                                multiple
                                value={selectedRoleKeys}
                                label="Material Roles"
                                onChange={(e) => {
                                    const value = e.target.value
                                    handleRoleChange(typeof value === 'string' ? [] : value as string[])
                                }}
                                renderValue={(selected) => (
                                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                        {selected.map((roleKey) => {
                                            const rc = roleConfigs.find(r => normalizeRoleKey(r.role) === roleKey)
                                            return <Chip key={roleKey} label={rc?.display_name || roleKey} size="small" />
                                        })}
                                    </Box>
                                )}
                            >
                                {selectableRoles.map(rc => {
                                    const skuPair = formatRoleSkuPair(rc.sku_abbrev_no_padding, rc.sku_abbrev_with_padding)
                                    return (
                                        <MenuItem key={rc.role} value={normalizeRoleKey(rc.role)}>
                                            {rc.display_name || rc.role} ({rc.role}) — {skuPair}
                                        </MenuItem>
                                    )
                                })}
                            </Select>
                        </FormControl>
                    </Grid>

                    {/* Color dropdowns - one per selected role */}
                    {selectedRoleKeys.map((roleKey) => {
                        const roleConfig = roleConfigs.find(rc => normalizeRoleKey(rc.role) === roleKey)
                        const colors = surchargesByRole[roleKey] || []

                        return (
                            <Grid item xs={12} key={roleKey}>
                                <FormControl fullWidth size="small">
                                    <InputLabel>Colors for {roleConfig?.display_name || roleKey}</InputLabel>
                                    <Select
                                        multiple
                                        value={selectedColourSurchargeIdsByRole[roleKey] || []}
                                        label={`Colors for ${roleConfig?.display_name || roleKey}`}
                                        onChange={(e) => {
                                            const value = e.target.value
                                            const newColors = typeof value === 'string' ? [] : value as number[]
                                            setSelectedColourSurchargeIdsByRole({
                                                ...selectedColourSurchargeIdsByRole,
                                                [roleKey]: newColors
                                            })
                                        }}
                                        renderValue={(selected) => (
                                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                                {selected.map((colorId) => {
                                                    const color = colors.find(c => c.id === colorId)
                                                    return (
                                                        <Chip
                                                            key={colorId}
                                                            label={color?.color_friendly_name || color?.colour || `ID ${colorId}`}
                                                            size="small"
                                                        />
                                                    )
                                                })}
                                            </Box>
                                        )}
                                    >
                                        {colors.map(color => (
                                            <MenuItem key={color.id} value={color.id}>
                                                {color.color_friendly_name || color.colour} (${color.surcharge.toFixed(2)})
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                        )
                    })}

                    <Grid item xs={12}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Design Options</InputLabel>
                            <Select
                                multiple
                                value={selectedDesignOptionIds}
                                label="Design Options"
                                onChange={(e) => {
                                    const value = e.target.value
                                    setSelectedDesignOptionIds(typeof value === 'string' ? [] : value as number[])
                                }}
                                renderValue={(selected) => (
                                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                        {selected.map((id) => {
                                            const opt = designOptions.find(o => o.id === id)
                                            return <Chip key={id} label={opt?.name || `ID ${id}`} size="small" />
                                        })}
                                    </Box>
                                )}
                            >
                                {ebayDesignOptions.map(opt => (
                                    <MenuItem key={opt.id} value={opt.id}>{opt.name}</MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Grid>

                </Grid>

                <Box sx={{ mt: 2 }}>
                    <Button variant="outlined" onClick={handleOpenCreatePreset}>
                        Save preset
                    </Button>
                </Box>

                {presetError && (
                    <Alert severity="error" sx={{ mt: 2 }}>
                        {presetError}
                    </Alert>
                )}

                <Box sx={{ mt: 3 }}>
                    <Typography variant="subtitle1" gutterBottom>Saved presets</Typography>

                    {assignedPresets.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" sx={{ mb: 1 }}>Assigned equipment types</Typography>
                            <Grid container spacing={1}>
                                {assignedPresets.map((entry) => (
                                    <Grid item xs={12} md={6} key={entry.id}>
                                        <Paper variant="outlined" sx={{ p: 1.5 }}>
                                            <Button
                                                variant="text"
                                                sx={{ p: 0, textTransform: 'none', fontWeight: 600, justifyContent: 'flex-start' }}
                                                onClick={() => { void handleOpenEditPreset(entry) }}
                                            >
                                                {entry.name}
                                            </Button>
                                            <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
                                                Assigned: {formatPresetEquipmentTypes(entry.equipment_type_ids || [])}
                                            </Typography>
                                            <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                                <Button size="small" onClick={() => { void handleLoadPreset(entry) }}>Load</Button>
                                                <Button size="small" onClick={() => handleOpenAssignPreset(entry)}>Assign equipment types</Button>
                                                <Button size="small" onClick={() => { void handleOpenEditPreset(entry) }}>Edit</Button>
                                                <Button size="small" color="error" onClick={() => { void handleDeletePreset(entry) }}>Delete</Button>
                                            </Box>
                                        </Paper>
                                    </Grid>
                                ))}
                            </Grid>
                        </Box>
                    )}

                    <Box>
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>Unassigned</Typography>
                        {unassignedPresets.length === 0 ? (
                            <Typography variant="body2" color="text.secondary">None</Typography>
                        ) : (
                            <Grid container spacing={1}>
                                {unassignedPresets.map((entry) => (
                                    <Grid item xs={12} md={6} key={entry.id}>
                                        <Paper variant="outlined" sx={{ p: 1.5 }}>
                                            <Button
                                                variant="text"
                                                sx={{ p: 0, textTransform: 'none', fontWeight: 600, justifyContent: 'flex-start' }}
                                                onClick={() => { void handleOpenEditPreset(entry) }}
                                            >
                                                {entry.name}
                                            </Button>
                                            <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
                                                Assigned: (none)
                                            </Typography>
                                            <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                                <Button size="small" onClick={() => { void handleLoadPreset(entry) }}>Load</Button>
                                                <Button size="small" onClick={() => handleOpenAssignPreset(entry)}>Assign equipment types</Button>
                                                <Button size="small" onClick={() => { void handleOpenEditPreset(entry) }}>Edit</Button>
                                                <Button size="small" color="error" onClick={() => { void handleDeletePreset(entry) }}>Delete</Button>
                                            </Box>
                                        </Paper>
                                    </Grid>
                                ))}
                            </Grid>
                        )}
                    </Box>
                </Box>
            </Paper>

            <Box sx={{ mt: 3 }}>
                <FormControl size="small" sx={{ minWidth: 200, mr: 2, mb: 2 }}>
                    <InputLabel>Padding Mode</InputLabel>
                    <Select
                        value={paddingMode}
                        label="Padding Mode"
                        onChange={(e) => setPaddingMode(e.target.value as 'both' | 'no_padding' | 'with_padding')}
                    >
                        <MenuItem value="both">Both</MenuItem>
                        <MenuItem value="no_padding">Non-padded only</MenuItem>
                        <MenuItem value="with_padding">Padded only</MenuItem>
                    </Select>
                </FormControl>
                <Box>
                <Button
                    variant="contained"
                    onClick={handleGenerateVariations}
                    disabled={!isGenerateEnabled || generatingVariations || !descriptionPreflight.canExport}
                    sx={{ mr: 2 }}
                >
                    {generatingVariations ? 'Generating...' : 'Generate Variations'}
                </Button>
                <Button
                    variant="contained"
                    color="secondary"
                    onClick={handleGenerateBaseVariants}
                    disabled={selectedModels.size === 0 || generatingVariations || !descriptionPreflight.canExport}
                    sx={{ mr: 2 }}
                >
                    {generatingVariations ? 'Generating...' : 'Generate Base Variants (C/CG/L/LG)'}
                </Button>
                <Button
                    variant="outlined"
                    onClick={handleLoadExisting}
                    disabled={selectedModels.size === 0 || loadingExisting}
                    sx={{ mr: 2 }}
                >
                    {loadingExisting ? 'Loading...' : 'Load Existing Variations'}
                </Button>
                <Button
                    variant="contained"
                    color="success"
                    onClick={handleExportCsv}
                    disabled={selectedModels.size === 0 || exportingCsv || !descriptionPreflight.canExport}
                    title={selectedModels.size === 0 ? "Select models to export" : "Download generated variations as CSV"}
                >
                    {exportingCsv ? 'Exporting...' : 'Download CSV'}
                </Button>
                </Box>
            </Box>

            {/* Error Display */}
            {variationError && (
                <Alert severity="error" sx={{ mt: 2, whiteSpace: 'pre-line' }}>
                    {variationError}
                </Alert>
            )}

            {/* Variation Preview Table */}
            {variationResult && variationResult.rows.length > 0 && (
                <Paper sx={{ mt: 3, p: 2 }}>
                    <Typography variant="h6" gutterBottom>
                        Generated Variations ({variationResult.created} created, {variationResult.updated} updated)
                    </Typography>
                    <Box sx={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '16px' }}>
                            <thead>
                                <tr style={{ borderBottom: '2px solid #ddd' }}>
                                    <th style={{ textAlign: 'left', padding: '8px' }}>Model ID</th>
                                    <th style={{ textAlign: 'left', padding: '8px' }}>SKU</th>
                                    <th style={{ textAlign: 'left', padding: '8px' }}>Material</th>
                                    <th style={{ textAlign: 'left', padding: '8px' }}>Color</th>
                                    <th style={{ textAlign: 'left', padding: '8px' }}>Design Options</th>
                                </tr>
                            </thead>
                            <tbody>
                                {variationResult.rows.map((row, idx) => (
                                    <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '8px' }}>{row.model_id}</td>
                                        <td style={{ padding: '8px', fontFamily: 'monospace' }}>{row.sku}</td>
                                        <td style={{ padding: '8px' }}>{row.material_id}</td>
                                        <td style={{ padding: '8px' }}>{row.material_colour_surcharge_id || '-'}</td>
                                        <td style={{ padding: '8px' }}>{row.design_option_ids.join(', ') || '-'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </Box>
                </Paper>
            )}

            {/* Existing Variations Table */}
            {existingVariations.length > 0 && (
                <Paper sx={{ mt: 3, p: 2 }}>
                    <Typography variant="h6" gutterBottom>
                        Existing Variations ({existingVariations.length} found)
                    </Typography>
                    <Box sx={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '16px' }}>
                            <thead>
                                <tr style={{ borderBottom: '2px solid #ddd' }}>
                                    <th style={{ textAlign: 'left', padding: '8px' }}>Model ID</th>
                                    <th style={{ textAlign: 'left', padding: '8px' }}>SKU</th>
                                    <th style={{ textAlign: 'left', padding: '8px' }}>Material</th>
                                    <th style={{ textAlign: 'left', padding: '8px' }}>Color</th>
                                    <th style={{ textAlign: 'left', padding: '8px' }}>Design Options</th>
                                </tr>
                            </thead>
                            <tbody>
                                {existingVariations.map((row, idx) => (
                                    <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '8px' }}>{row.model_id}</td>
                                        <td style={{ padding: '8px', fontFamily: 'monospace' }}>{row.sku}</td>
                                        <td style={{ padding: '8px' }}>{formatMaterialDisplay(row.material_id)}</td>
                                        <td style={{ padding: '8px' }}>{formatColorDisplay(row.material_colour_surcharge_id, Object.values(surchargesByRole).flat())}</td>
                                        <td style={{ padding: '8px' }}>{formatDesignOptionsDisplay(row.design_option_ids)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </Box>
                </Paper>
            )}

            {/* Selected Variation Summary (Read-Only) */}
            {selectedRoleKeys.length > 0 && (
                <Box sx={{ mt: 3, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
                    <Typography variant="subtitle2" gutterBottom>
                        Selected Variation Summary (Read-Only)
                    </Typography>

                    {/* Active Role Assignments */}
                    <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" fontWeight="bold" gutterBottom>
                            Active Role Assignments:
                        </Typography>
                        {selectedRoleKeys.map(roleKey => {
                            const activeAssignment = resolveActiveAssignmentForRole(roleKey)
                            const material = materials.find(m => m.id === activeAssignment?.material_id)
                            const roleConfig = roleConfigs.find(rc => normalizeRoleKey(rc.role) === roleKey)
                            const skuPair = formatRoleSkuPair(roleConfig?.sku_abbrev_no_padding, roleConfig?.sku_abbrev_with_padding)
                            const selectedColors = selectedColourSurchargeIdsByRole[roleKey] || []
                            const roleColors = surchargesByRole[roleKey] || []

                            return (
                                <Box key={roleKey} sx={{ mb: 1 }}>
                                    <Typography variant="body2" color="text.secondary" sx={{ pl: 2 }}>
                                        • Role: {roleConfig?.display_name || roleKey} ({roleKey})
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary" sx={{ pl: 4 }}>
                                        Material: {material?.name || 'Unknown Material'}
                                        {activeAssignment ? ` (effective ${new Date(activeAssignment.effective_date).toLocaleDateString()})` : ''}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary" sx={{ pl: 4 }}>
                                        Role assignment SKU: {skuPair}
                                    </Typography>
                                    {selectedColors.length > 0 && (
                                        <Typography variant="body2" color="text.secondary" sx={{ pl: 4 }}>
                                            Colors: {selectedColors.map(colorId => {
                                                const color = roleColors.find(c => c.id === colorId)
                                                if (!color) return `ID ${colorId}`
                                                const name = color.color_friendly_name || color.colour
                                                const abbrev = color.sku_abbreviation ? color.sku_abbreviation.trim() : null
                                                return `${name} (abbrev: ${formatAbbrev(abbrev)}, $${color.surcharge.toFixed(2)})`
                                            }).join(', ')}
                                        </Typography>
                                    )}
                                </Box>
                            )
                        })}
                    </Box>

                    {selectedDesignOptionIds.length > 0 && (
                        <Box>
                            <Typography variant="body2" fontWeight="bold">
                                Design Option Abbreviations:
                            </Typography>
                            {selectedDesignOptionIds
                                .map(id => designOptions.find(opt => opt.id === id))
                                .filter(Boolean)
                                .sort((a, b) => (a?.id || 0) - (b?.id || 0))
                                .map(opt => (
                                    <Typography key={opt?.id} variant="body2" color="text.secondary" sx={{ pl: 2 }}>
                                        • {opt?.name} — Abbrev: {formatAbbrev(opt?.sku_abbreviation)}
                                    </Typography>
                                ))}
                        </Box>
                    )}
                </Box>
            )}

            <Dialog open={savePresetOpen} onClose={() => setSavePresetOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>{editingPresetId ? 'Edit preset' : 'Save preset'}</DialogTitle>
                <DialogContent>
                    <TextField
                        autoFocus
                        fullWidth
                        size="small"
                        margin="dense"
                        label="Name"
                        value={savePresetName}
                        onChange={(e) => setSavePresetName(e.target.value)}
                    />
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', mb: 1.5 }}>
                        Edit variation inputs below, then {editingPresetId ? 'update' : 'save'} this preset.
                    </Typography>

                    <Grid container spacing={1.5}>
                        <Grid item xs={12}>
                            <FormControl fullWidth size="small">
                                <InputLabel>Material Roles</InputLabel>
                                <Select
                                    multiple
                                    value={selectedRoleKeys}
                                    label="Material Roles"
                                    onChange={(e) => {
                                        const value = e.target.value
                                        handleRoleChange(typeof value === 'string' ? [] : value as string[])
                                    }}
                                    renderValue={(selected) => (
                                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                            {selected.map((roleKey) => {
                                                const rc = roleConfigs.find(r => normalizeRoleKey(r.role) === roleKey)
                                                return <Chip key={roleKey} label={rc?.display_name || roleKey} size="small" />
                                            })}
                                        </Box>
                                    )}
                                >
                                    {selectableRoles.map(rc => {
                                        const skuPair = formatRoleSkuPair(rc.sku_abbrev_no_padding, rc.sku_abbrev_with_padding)
                                        return (
                                            <MenuItem key={rc.role} value={normalizeRoleKey(rc.role)}>
                                                {rc.display_name || rc.role} ({rc.role}) - {skuPair}
                                            </MenuItem>
                                        )
                                    })}
                                </Select>
                            </FormControl>
                        </Grid>

                        {selectedRoleKeys.map((roleKey) => {
                            const roleConfig = roleConfigs.find(rc => normalizeRoleKey(rc.role) === roleKey)
                            const colors = surchargesByRole[roleKey] || []
                            return (
                                <Grid item xs={12} key={`preset-dialog-${roleKey}`}>
                                    <FormControl fullWidth size="small">
                                        <InputLabel>Colors for {roleConfig?.display_name || roleKey}</InputLabel>
                                        <Select
                                            multiple
                                            value={selectedColourSurchargeIdsByRole[roleKey] || []}
                                            label={`Colors for ${roleConfig?.display_name || roleKey}`}
                                            onChange={(e) => {
                                                const value = e.target.value
                                                const newColors = typeof value === 'string' ? [] : value as number[]
                                                setSelectedColourSurchargeIdsByRole({
                                                    ...selectedColourSurchargeIdsByRole,
                                                    [roleKey]: newColors
                                                })
                                            }}
                                            renderValue={(selected) => (
                                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                                    {selected.map((colorId) => {
                                                        const color = colors.find(c => c.id === colorId)
                                                        return (
                                                            <Chip
                                                                key={colorId}
                                                                label={color?.color_friendly_name || color?.colour || `ID ${colorId}`}
                                                                size="small"
                                                            />
                                                        )
                                                    })}
                                                </Box>
                                            )}
                                        >
                                            {colors.map(color => (
                                                <MenuItem key={color.id} value={color.id}>
                                                    {color.color_friendly_name || color.colour} (${color.surcharge.toFixed(2)})
                                                </MenuItem>
                                            ))}
                                        </Select>
                                    </FormControl>
                                </Grid>
                            )
                        })}

                        <Grid item xs={12}>
                            <FormControl fullWidth size="small">
                                <InputLabel>Design Options</InputLabel>
                                <Select
                                    multiple
                                    value={selectedDesignOptionIds}
                                    label="Design Options"
                                    onChange={(e) => {
                                        const value = e.target.value
                                        setSelectedDesignOptionIds(typeof value === 'string' ? [] : value as number[])
                                    }}
                                    renderValue={(selected) => (
                                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                            {selected.map((id) => {
                                                const opt = designOptions.find(o => o.id === id)
                                                return <Chip key={id} label={opt?.name || `ID ${id}`} size="small" />
                                            })}
                                        </Box>
                                    )}
                                >
                                    {ebayDesignOptions.map(opt => (
                                        <MenuItem key={opt.id} value={opt.id}>{opt.name}</MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>
                    </Grid>
                    {presetError && (
                        <Alert severity="error" sx={{ mt: 2 }}>
                            {presetError}
                        </Alert>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setSavePresetOpen(false)}>Cancel</Button>
                    <Button
                        variant="contained"
                        onClick={handleSavePreset}
                        disabled={presetSaving || !savePresetName.trim()}
                    >
                        {editingPresetId ? 'Update' : 'Save'}
                    </Button>
                </DialogActions>
            </Dialog>

            <Dialog open={assignPresetOpen} onClose={() => setAssignPresetOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Assign equipment types</DialogTitle>
                <DialogContent>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                        {assignPresetEntry?.name || ''}
                    </Typography>
                    <FormControl fullWidth size="small" sx={{ mt: 1 }}>
                        <InputLabel>Equipment Types</InputLabel>
                        <Select
                            multiple
                            value={assignEquipmentTypeIds}
                            label="Equipment Types"
                            onChange={(e) => {
                                const value = e.target.value
                                setAssignEquipmentTypeIds(typeof value === 'string' ? [] : (value as number[]))
                            }}
                            renderValue={(selected) => (
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                    {selected.map((id) => (
                                        <Chip
                                            key={id}
                                            label={equipmentTypes.find((et) => et.id === id)?.name || `ID ${id}`}
                                            size="small"
                                        />
                                    ))}
                                </Box>
                            )}
                        >
                            {equipmentTypes.map((et) => (
                                <MenuItem key={et.id} value={et.id}>{et.name}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    {assignError && (
                        <Alert severity="error" sx={{ mt: 2 }}>
                            {assignError}
                        </Alert>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setAssignPresetOpen(false)}>Cancel</Button>
                    <Button variant="contained" onClick={handleSavePresetAssignments}>Save assignments</Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}
