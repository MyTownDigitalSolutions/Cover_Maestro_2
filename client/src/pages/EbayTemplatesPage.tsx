import React, { useState, useEffect, useMemo } from 'react'
import {
    Box, Typography, Paper, Button, Alert,
    Divider, IconButton, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, Chip, Stack, TextField,
    InputAdornment, Dialog, DialogTitle, DialogContent,
    DialogActions, Switch, FormControlLabel, Menu, MenuItem, Snackbar,
    FormControl, Select
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import RefreshIcon from '@mui/icons-material/Refresh'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import SearchIcon from '@mui/icons-material/Search'
import CloseIcon from '@mui/icons-material/Close'
import AddIcon from '@mui/icons-material/Add'
import VisibilityIcon from '@mui/icons-material/Visibility'
import DownloadIcon from '@mui/icons-material/Download'
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown'
import GridOnIcon from '@mui/icons-material/GridOn'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'

import {
    ebayTemplatesApi, equipmentTypesApi, settingsApi, EbayTemplateResponse, EbayTemplateParseSummary,
    EbayFieldResponse, EbayValidValueDetailed, EbayTemplatePreviewResponse,
    EbayTemplateIntegrityResponse, EbayTemplateVerificationResponse, EbayTemplateScanResponse,
    TemplateFieldAssetResponse, TemplateFieldAssetType
} from '../services/api'
import type { EquipmentType } from '../types'

type EbayRowScope = 'both' | 'parent_only' | 'variation_only'

const getRowScopeValue = (field: EbayFieldResponse): EbayRowScope => {
    const value = field.row_scope
    return value === 'parent_only' || value === 'variation_only' ? value : 'both'
}

const isDescriptionField = (fieldName: string | undefined): boolean =>
    String(fieldName || '').replace(/\s+/g, '').toLowerCase() === 'description'

const isImageUrlField = (fieldName: string | undefined): boolean => {
    const key = String(fieldName || '').replace(/\s+/g, '').toLowerCase()
    return [
        'itemphotourl',
        'itemphotourls',
        'pictureurl',
        'pictureurls',
        'photourl',
        'photourls',
        'imageurl',
        'imageurls'
    ].includes(key)
}

const isAssetManagedField = (field: EbayFieldResponse | null | undefined): boolean => {
    return Boolean(field?.is_asset_managed)
}

// --- Component: Valid Values Section in Modal ---
const ValidValuesSection = ({
    values,
    valuesDetailed,
    rowScope,
    selectedValue,
    parentSelectedValue,
    variationSelectedValue,
    onChipClick,
    onParentChipClick,
    onVariationChipClick,
    onDeleteValue,
    newValue,
    onNewValueChange,
    onAddValue,
    savingAdd
}: {
    values: string[],
    valuesDetailed?: EbayValidValueDetailed[],
    rowScope: EbayRowScope,
    selectedValue: string | null | undefined,
    parentSelectedValue?: string | null,
    variationSelectedValue?: string | null,
    onChipClick: (value: string) => void,
    onParentChipClick?: (value: string) => void,
    onVariationChipClick?: (value: string) => void,
    onDeleteValue: (valueId: number, valueName: string) => void,
    newValue: string,
    onNewValueChange: (value: string) => void,
    onAddValue: () => void,
    savingAdd: boolean
}) => {
    const [searchTerm, setSearchTerm] = useState('')

    const filteredValues = useMemo(() => {
        if (valuesDetailed && valuesDetailed.length > 0) {
            // Use detailed values if available
            if (!searchTerm) return valuesDetailed
            return valuesDetailed.filter(v => v.value.toLowerCase().includes(searchTerm.toLowerCase()))
        } else {
            // Fallback to string array
            if (!values) return []
            if (!searchTerm) return values.map((v, i) => ({ id: i, value: v }))
            return values.filter(v => v.toLowerCase().includes(searchTerm.toLowerCase())).map((v, i) => ({ id: i, value: v }))
        }
    }, [values, valuesDetailed, searchTerm])

    const canAdd = newValue.trim().length > 0 && !savingAdd

    return (
        <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
                Valid Values ({values?.length || 0})
            </Typography>

            <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                <TextField
                    placeholder="Search values..."
                    size="small"
                    fullWidth
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    InputProps={{
                        startAdornment: (
                            <InputAdornment position="start">
                                <SearchIcon fontSize="small" />
                            </InputAdornment>
                        )
                    }}
                />
            </Stack>

            <Box sx={{
                maxHeight: 200,
                overflowY: 'auto',
                bgcolor: 'background.paper',
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
                p: 1.5,
                mb: 2
            }}>
                {filteredValues && filteredValues.length > 0 ? (
                    rowScope === 'both' ? (
                        <Stack spacing={1.25}>
                            <Box>
                                <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                                    Parent
                                </Typography>
                                <Stack direction="row" flexWrap="wrap" gap={1}>
                                    {filteredValues.map((v) => (
                                        <Chip
                                            key={`parent-${v.id}`}
                                            label={v.value}
                                            size="small"
                                            color={parentSelectedValue === v.value ? "primary" : "default"}
                                            variant={parentSelectedValue === v.value ? "filled" : "outlined"}
                                            onClick={() => onParentChipClick?.(v.value)}
                                            onDelete={valuesDetailed && valuesDetailed.length > 0 ? (e) => {
                                                e.stopPropagation()
                                                if (window.confirm(`Delete value "${v.value}"?`)) {
                                                    onDeleteValue(v.id, v.value)
                                                }
                                            } : undefined}
                                            sx={{ cursor: 'pointer' }}
                                        />
                                    ))}
                                </Stack>
                            </Box>
                            <Box>
                                <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                                    Variation
                                </Typography>
                                <Stack direction="row" flexWrap="wrap" gap={1}>
                                    {filteredValues.map((v) => (
                                        <Chip
                                            key={`variation-${v.id}`}
                                            label={v.value}
                                            size="small"
                                            color={variationSelectedValue === v.value ? "primary" : "default"}
                                            variant={variationSelectedValue === v.value ? "filled" : "outlined"}
                                            onClick={() => onVariationChipClick?.(v.value)}
                                            onDelete={valuesDetailed && valuesDetailed.length > 0 ? (e) => {
                                                e.stopPropagation()
                                                if (window.confirm(`Delete value "${v.value}"?`)) {
                                                    onDeleteValue(v.id, v.value)
                                                }
                                            } : undefined}
                                            sx={{ cursor: 'pointer' }}
                                        />
                                    ))}
                                </Stack>
                            </Box>
                        </Stack>
                    ) : (
                        <Stack direction="row" flexWrap="wrap" gap={1}>
                            {filteredValues.map((v) => (
                                <Chip
                                    key={v.id}
                                    label={v.value}
                                    size="small"
                                    color={selectedValue === v.value ? "primary" : "default"}
                                    variant={selectedValue === v.value ? "filled" : "outlined"}
                                    onClick={() => onChipClick(v.value)}
                                    onDelete={selectedValue === v.value
                                        ? () => onChipClick("")
                                        : (valuesDetailed && valuesDetailed.length > 0 ? (e) => {
                                            e.stopPropagation()
                                            if (window.confirm(`Delete value "${v.value}"?`)) {
                                                onDeleteValue(v.id, v.value)
                                            }
                                        } : undefined)}
                                    sx={{ cursor: 'pointer' }}
                                />
                            ))}
                            {filteredValues.length === 0 && (
                                <Typography variant="caption" color="text.secondary">No matching values found</Typography>
                            )}
                        </Stack>
                    )
                ) : (
                    <Typography variant="caption" color="text.secondary">No valid values defined.</Typography>
                )}
            </Box>

            {/* Add Value Area */}
            <Stack direction="row" spacing={1}>
                <TextField
                    size="small"
                    placeholder="Add new value..."
                    value={newValue}
                    onChange={(e) => onNewValueChange(e.target.value)}
                    onKeyPress={(e) => {
                        if (e.key === 'Enter' && canAdd) {
                            onAddValue()
                        }
                    }}
                    disabled={savingAdd}
                    fullWidth
                    helperText={savingAdd ? "Saving..." : "Press Enter or click Add"}
                />
                <Button
                    variant="contained"
                    onClick={onAddValue}
                    disabled={!canAdd}
                    startIcon={<AddIcon />}
                >
                    Add
                </Button>
            </Stack>
        </Box>
    )
}

// --- Component: Field Details Modal ---
const FieldDetailsModal = ({
    open,
    field,
    onClose,
    onFieldUpdated
}: {
    open: boolean,
    field: EbayFieldResponse | null,
    onClose: () => void,
    onFieldUpdated: (updatedField: EbayFieldResponse) => void
}) => {
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [localField, setLocalField] = useState<EbayFieldResponse | null>(field)
    const [newValue, setNewValue] = useState('')
    const [savingAdd, setSavingAdd] = useState(false)
    const [parentCustomDraft, setParentCustomDraft] = useState('')
    const [variationCustomDraft, setVariationCustomDraft] = useState('')
    const [equipmentTypes, setEquipmentTypes] = useState<EquipmentType[]>([])
    const [fieldAssets, setFieldAssets] = useState<TemplateFieldAssetResponse[]>([])
    const [assetsLoading, setAssetsLoading] = useState(false)
    const [assetsSaving, setAssetsSaving] = useState(false)
    const [descriptionAssetId, setDescriptionAssetId] = useState<number | null>(null)
    const [descriptionNameDraft, setDescriptionNameDraft] = useState('')
    const [descriptionIsFallback, setDescriptionIsFallback] = useState(true)
    const [descriptionEquipmentTypeIds, setDescriptionEquipmentTypeIds] = useState<number[]>([])
    const [descriptionValueDraft, setDescriptionValueDraft] = useState('')
    const [parentPatternAssetId, setParentPatternAssetId] = useState<number | null>(null)
    const [parentPatternNameDraft, setParentPatternNameDraft] = useState('')
    const [parentPatternSeparatorDraft, setParentPatternSeparatorDraft] = useState('|')
    const [parentPatternIsFallback, setParentPatternIsFallback] = useState(true)
    const [parentPatternEquipmentTypeIds, setParentPatternEquipmentTypeIds] = useState<number[]>([])
    const [parentPatternValueDraft, setParentPatternValueDraft] = useState('')
    const [variationPatternAssetId, setVariationPatternAssetId] = useState<number | null>(null)
    const [variationPatternNameDraft, setVariationPatternNameDraft] = useState('')
    const [variationPatternSeparatorDraft, setVariationPatternSeparatorDraft] = useState('|')
    const [variationPatternPrefixDraft, setVariationPatternPrefixDraft] = useState('')
    const [variationPatternIsFallback, setVariationPatternIsFallback] = useState(true)
    const [variationPatternEquipmentTypeIds, setVariationPatternEquipmentTypeIds] = useState<number[]>([])
    const [variationPatternValueDraft, setVariationPatternValueDraft] = useState('')
    const [descriptionSelectionMode, setDescriptionSelectionMode] = useState<'GLOBAL_PRIMARY' | 'EQUIPMENT_TYPE_PRIMARY'>('GLOBAL_PRIMARY')
    const [assignDialogOpen, setAssignDialogOpen] = useState(false)
    const [assignAssetId, setAssignAssetId] = useState<number | null>(null)
    const [assignEquipmentTypeIds, setAssignEquipmentTypeIds] = useState<number[]>([])
    const [assignError, setAssignError] = useState<string | null>(null)
    const [assignSaving, setAssignSaving] = useState(false)

    // Update local field when prop changes
    useEffect(() => {
        setLocalField(field)
        setParentCustomDraft(field?.parent_custom_value || '')
        setVariationCustomDraft(field?.variation_custom_value || '')
        setError(null)
    }, [field])

    useEffect(() => {
        const loadFieldAssets = async () => {
            if (!field || (!isDescriptionField(field.field_name) && !isImageUrlField(field.field_name))) {
                setEquipmentTypes([])
                setFieldAssets([])
                return
            }
            setAssetsLoading(true)
            try {
                const [types, rows] = await Promise.all([
                    equipmentTypesApi.list(),
                    ebayTemplatesApi.getFieldAssets(field.id),
                ])
                setEquipmentTypes(types)
                setFieldAssets(rows)
                try {
                    const exportSettings = await settingsApi.getExport()
                    const mode = exportSettings.ebay_description_selection_mode
                    setDescriptionSelectionMode(mode === 'EQUIPMENT_TYPE_PRIMARY' ? 'EQUIPMENT_TYPE_PRIMARY' : 'GLOBAL_PRIMARY')
                } catch {
                    setDescriptionSelectionMode('GLOBAL_PRIMARY')
                }
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Failed to load field assets')
            } finally {
                setAssetsLoading(false)
            }
        }
        loadFieldAssets()
    }, [field])

    useEffect(() => {
        setDescriptionAssetId(null)
        setDescriptionNameDraft('')
        setDescriptionIsFallback(true)
        setDescriptionEquipmentTypeIds([])
        setDescriptionValueDraft('')
        setParentPatternAssetId(null)
        setParentPatternNameDraft('')
        setParentPatternSeparatorDraft('|')
        setParentPatternIsFallback(true)
        setParentPatternEquipmentTypeIds([])
        setParentPatternValueDraft('')
        setVariationPatternAssetId(null)
        setVariationPatternNameDraft('')
        setVariationPatternSeparatorDraft('|')
        setVariationPatternPrefixDraft('')
        setVariationPatternIsFallback(true)
        setVariationPatternEquipmentTypeIds([])
        setVariationPatternValueDraft('')
    }, [field?.id])

    useEffect(() => {
        if (!field || !isImageUrlField(field.field_name)) return
        const parentAssets = fieldAssets.filter((a) => a.asset_type === 'image_parent_pattern')
        const variationAssets = fieldAssets.filter((a) => a.asset_type === 'image_variation_pattern')
        if (parentPatternAssetId == null && parentAssets.length > 0) {
            const parsedParent = parseImagePatternMetadata(parentAssets[0].value || '')
            setParentPatternSeparatorDraft(parsedParent.separator || '|')
        }
        if (variationPatternAssetId == null && variationAssets.length > 0) {
            const parsedVariation = parseImagePatternMetadata(variationAssets[0].value || '')
            setVariationPatternSeparatorDraft(parsedVariation.separator || '|')
            setVariationPatternPrefixDraft(parsedVariation.variationPrefix || '')
        }
    }, [field?.id, fieldAssets, parentPatternAssetId, variationPatternAssetId])

    if (!localField) return null

    const descriptionAssets = fieldAssets.filter(a => a.asset_type === 'description_html')
    const parentPatternAssets = fieldAssets.filter(a => a.asset_type === 'image_parent_pattern')
    const variationPatternAssets = fieldAssets.filter(a => a.asset_type === 'image_variation_pattern')

    const resetAssetDrafts = () => {
        setDescriptionAssetId(null)
        setDescriptionNameDraft('')
        setDescriptionIsFallback(true)
        setDescriptionEquipmentTypeIds([])
        setDescriptionValueDraft('')
        setParentPatternAssetId(null)
        setParentPatternNameDraft('')
        setParentPatternSeparatorDraft('|')
        setParentPatternIsFallback(true)
        setParentPatternEquipmentTypeIds([])
        setParentPatternValueDraft('')
        setVariationPatternAssetId(null)
        setVariationPatternNameDraft('')
        setVariationPatternSeparatorDraft('|')
        setVariationPatternPrefixDraft('')
        setVariationPatternIsFallback(true)
        setVariationPatternEquipmentTypeIds([])
        setVariationPatternValueDraft('')
    }

    const equipmentTypeName = (equipmentTypeId: number) =>
        equipmentTypes.find(et => et.id === equipmentTypeId)?.name || `Equipment Type #${equipmentTypeId}`

    const parseImagePatternMetadata = (rawValue: string | null | undefined): { separator: string, variationPrefix: string, pattern: string } => {
        const text = String(rawValue || '')
        let remaining = text
        let separator = '|'
        let variationPrefix = ''
        while (true) {
            const sep = remaining.match(/^\[\[SEP:(.)\]\]([\s\S]*)$/)
            if (sep) {
                separator = sep[1] || '|'
                remaining = sep[2] || ''
                continue
            }
            const vpfx = remaining.match(/^\[\[VPFX:(.*?)\]\]([\s\S]*)$/)
            if (vpfx) {
                variationPrefix = vpfx[1] || ''
                remaining = vpfx[2] || ''
                continue
            }
            break
        }
        return { separator, variationPrefix, pattern: remaining }
    }

    const composeImagePatternValue = (pattern: string, separator: string, variationPrefix?: string): string => {
        const sep = String(separator || '').trim().charAt(0) || '|'
        const vpfx = String(variationPrefix || '')
        return `[[SEP:${sep}]]${vpfx ? `[[VPFX:${vpfx}]]` : ''}${pattern}`
    }

    const refreshFieldAssets = async () => {
        if (!localField || (!isDescriptionField(localField.field_name) && !isImageUrlField(localField.field_name))) {
            return
        }
        const rows = await ebayTemplatesApi.getFieldAssets(localField.id)
        setFieldAssets(rows)
    }

    const saveAsset = async (
        assetType: TemplateFieldAssetType,
        assetId: number | null,
        name: string | null,
        value: string,
        isFallback: boolean,
        equipmentTypeIds: number[],
    ) => {
        const payload = {
            asset_type: assetType,
            name,
            value,
            is_default_fallback: isFallback,
            equipment_type_ids: isFallback ? [] : equipmentTypeIds,
        }
        if (assetId == null) {
            await ebayTemplatesApi.createFieldAsset(localField.id, payload)
        } else {
            const updatePayload: {
                value: string
                is_default_fallback: boolean
                equipment_type_ids: number[]
                name?: string
            } = {
                value: payload.value,
                is_default_fallback: payload.is_default_fallback,
                equipment_type_ids: payload.equipment_type_ids,
            }
            if (typeof payload.name === 'string' && payload.name.trim()) {
                updatePayload.name = payload.name.trim()
            }
            await ebayTemplatesApi.updateFieldAsset(localField.id, assetId, {
                ...updatePayload,
            })
        }
    }

    const beginEditAsset = (asset: TemplateFieldAssetResponse) => {
        resetAssetDrafts()
        if (asset.asset_type === 'description_html') {
            setDescriptionAssetId(asset.id)
            setDescriptionNameDraft(asset.name || '')
            setDescriptionIsFallback(asset.is_default_fallback)
            setDescriptionEquipmentTypeIds(asset.equipment_type_ids || [])
            setDescriptionValueDraft(asset.value || '')
            return
        }
        if (asset.asset_type === 'image_parent_pattern') {
            const parsed = parseImagePatternMetadata(asset.value || '')
            setParentPatternAssetId(asset.id)
            setParentPatternNameDraft(asset.name || '')
            setParentPatternSeparatorDraft(parsed.separator)
            setParentPatternIsFallback(asset.is_default_fallback)
            setParentPatternEquipmentTypeIds(asset.equipment_type_ids || [])
            setParentPatternValueDraft(parsed.pattern)
            return
        }
        const parsed = parseImagePatternMetadata(asset.value || '')
        setVariationPatternAssetId(asset.id)
        setVariationPatternNameDraft(asset.name || '')
        setVariationPatternSeparatorDraft(parsed.separator)
        setVariationPatternPrefixDraft(parsed.variationPrefix)
        setVariationPatternIsFallback(asset.is_default_fallback)
        setVariationPatternEquipmentTypeIds(asset.equipment_type_ids || [])
        setVariationPatternValueDraft(parsed.pattern)
    }

    const handleRequiredToggle = async (checked: boolean) => {
        setSaving(true)
        setError(null)
        try {
            const updated = await ebayTemplatesApi.updateField(localField.id, { required: checked })
            setLocalField(updated)
            onFieldUpdated(updated)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update required status')
            // Revert by resetting localField
            setLocalField(localField)
        } finally {
            setSaving(false)
        }
    }

    const handleChipClick = async (value: string) => {
        setSaving(true)
        setError(null)
        try {
            const normalizedValue = value && value.trim() !== '' ? value : null
            const updated = await ebayTemplatesApi.updateField(localField.id, {
                selected_value: normalizedValue,
                custom_value: null
            })
            setLocalField(updated)
            onFieldUpdated(updated)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update selected value')
        } finally {
            setSaving(false)
        }
    }

    const handleParentChipClick = async (value: string) => {
        setSaving(true)
        setError(null)
        try {
            const nextValue = localField.parent_selected_value === value ? null : value
            const updated = await ebayTemplatesApi.updateField(localField.id, {
                parent_selected_value: nextValue
            })
            setLocalField(updated)
            onFieldUpdated(updated)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update parent selected value')
        } finally {
            setSaving(false)
        }
    }

    const handleVariationChipClick = async (value: string) => {
        setSaving(true)
        setError(null)
        try {
            const nextValue = localField.variation_selected_value === value ? null : value
            const updated = await ebayTemplatesApi.updateField(localField.id, {
                variation_selected_value: nextValue
            })
            setLocalField(updated)
            onFieldUpdated(updated)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update variation selected value')
        } finally {
            setSaving(false)
        }
    }

    const saveParentCustomDraft = async () => {
        setSaving(true)
        setError(null)
        try {
            const trimmed = parentCustomDraft.trim()
            const updated = await ebayTemplatesApi.updateField(localField.id, {
                parent_custom_value: trimmed ? trimmed : null
            })
            setLocalField(updated)
            setParentCustomDraft(updated.parent_custom_value || '')
            onFieldUpdated(updated)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update parent custom value')
        } finally {
            setSaving(false)
        }
    }

    const saveVariationCustomDraft = async () => {
        setSaving(true)
        setError(null)
        try {
            const trimmed = variationCustomDraft.trim()
            const updated = await ebayTemplatesApi.updateField(localField.id, {
                variation_custom_value: trimmed ? trimmed : null
            })
            setLocalField(updated)
            setVariationCustomDraft(updated.variation_custom_value || '')
            onFieldUpdated(updated)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update variation custom value')
        } finally {
            setSaving(false)
        }
    }

    const handleAddValue = async () => {
        const trimmedValue = newValue.trim()
        if (!trimmedValue) return

        setSavingAdd(true)
        setError(null)
        try {
            const updated = await ebayTemplatesApi.addValidValue(localField.id, trimmedValue)
            setLocalField(updated)
            onFieldUpdated(updated)
            setNewValue('') // Clear input on success
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to add valid value')
        } finally {
            setSavingAdd(false)
        }
    }

    const handleDeleteValue = async (valueId: number, valueName: string) => {
        setSaving(true)
        setError(null)
        try {
            const updated = await ebayTemplatesApi.deleteValidValue(localField.id, valueId)
            setLocalField(updated)
            onFieldUpdated(updated)
        } catch (err: any) {
            setError(err.response?.data?.detail || `Failed to delete value "${valueName}"`)
        } finally {
            setSaving(false)
        }
    }

    const handleSaveDescriptionAsset = async () => {
        if (!localField || !isDescriptionField(localField.field_name)) return
        setAssetsSaving(true)
        setError(null)
        try {
            await saveAsset(
                'description_html',
                descriptionAssetId,
                descriptionNameDraft.trim() || null,
                descriptionValueDraft,
                descriptionIsFallback,
                descriptionEquipmentTypeIds,
            )
            await refreshFieldAssets()
            setDescriptionAssetId(null)
            setDescriptionNameDraft('')
            setDescriptionIsFallback(true)
            setDescriptionEquipmentTypeIds([])
            setDescriptionValueDraft('')
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save description asset')
        } finally {
            setAssetsSaving(false)
        }
    }

    const handleSaveImagePatternAsset = async (assetType: 'image_parent_pattern' | 'image_variation_pattern') => {
        if (!localField || !isImageUrlField(localField.field_name)) return
        setAssetsSaving(true)
        setError(null)
        try {
            if (assetType === 'image_parent_pattern') {
                await saveAsset(
                    assetType,
                    parentPatternAssetId,
                    parentPatternNameDraft.trim() || null,
                    composeImagePatternValue(parentPatternValueDraft, parentPatternSeparatorDraft),
                    parentPatternIsFallback,
                    parentPatternEquipmentTypeIds,
                )
                setParentPatternAssetId(null)
                setParentPatternNameDraft('')
                setParentPatternSeparatorDraft('|')
                setParentPatternIsFallback(true)
                setParentPatternEquipmentTypeIds([])
                setParentPatternValueDraft('')
            } else {
                await saveAsset(
                    assetType,
                    variationPatternAssetId,
                    variationPatternNameDraft.trim() || null,
                    composeImagePatternValue(variationPatternValueDraft, variationPatternSeparatorDraft, variationPatternPrefixDraft),
                    variationPatternIsFallback,
                    variationPatternEquipmentTypeIds,
                )
                setVariationPatternAssetId(null)
                setVariationPatternNameDraft('')
                setVariationPatternSeparatorDraft('|')
                setVariationPatternPrefixDraft('')
                setVariationPatternIsFallback(true)
                setVariationPatternEquipmentTypeIds([])
                setVariationPatternValueDraft('')
            }
            await refreshFieldAssets()
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save image pattern asset')
        } finally {
            setAssetsSaving(false)
        }
    }

    const handleSaveImageFieldSettings = async () => {
        if (!localField || !isImageUrlField(localField.field_name)) return
        if ((parentPatternAssets.length + variationPatternAssets.length) === 0) return
        setAssetsSaving(true)
        setError(null)
        try {
            const parentSeparator = String(parentPatternSeparatorDraft || '').trim().charAt(0) || '|'
            const variationSeparator = String(variationPatternSeparatorDraft || '').trim().charAt(0) || '|'
            const variationPrefix = String(variationPatternPrefixDraft || '')

            for (const entry of parentPatternAssets) {
                const parsed = parseImagePatternMetadata(entry.value || '')
                await ebayTemplatesApi.updateFieldAsset(localField.id, entry.id, {
                    value: composeImagePatternValue(parsed.pattern, parentSeparator),
                    name: entry.name,
                    is_default_fallback: Boolean(entry.is_default_fallback),
                    equipment_type_ids: entry.is_default_fallback ? [] : (entry.equipment_type_ids || []),
                })
            }

            for (const entry of variationPatternAssets) {
                const parsed = parseImagePatternMetadata(entry.value || '')
                await ebayTemplatesApi.updateFieldAsset(localField.id, entry.id, {
                    value: composeImagePatternValue(parsed.pattern, variationSeparator, variationPrefix),
                    name: entry.name,
                    is_default_fallback: Boolean(entry.is_default_fallback),
                    equipment_type_ids: entry.is_default_fallback ? [] : (entry.equipment_type_ids || []),
                })
            }

            await refreshFieldAssets()
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save image field settings')
        } finally {
            setAssetsSaving(false)
        }
    }

    const handleDeleteAsset = async (assetId: number) => {
        if (!localField) return
        setAssetsSaving(true)
        setError(null)
        try {
            await ebayTemplatesApi.deleteFieldAsset(localField.id, assetId)
            await refreshFieldAssets()
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to delete asset')
        } finally {
            setAssetsSaving(false)
        }
    }

    const openAssignDialog = (asset: TemplateFieldAssetResponse) => {
        setAssignAssetId(asset.id)
        setAssignEquipmentTypeIds((asset.equipment_type_ids || []).map((id) => Number(id)))
        setAssignError(null)
        setAssignDialogOpen(true)
    }

    const closeAssignDialog = () => {
        if (assignSaving) return
        setAssignDialogOpen(false)
        setAssignAssetId(null)
        setAssignEquipmentTypeIds([])
        setAssignError(null)
    }

    const handleSaveAssignments = async () => {
        if (!localField || assignAssetId == null) return
        const targetAsset = fieldAssets.find((entry) => entry.id === assignAssetId)
        if (!targetAsset) {
            setAssignError('Selected asset was not found')
            return
        }
        if (typeof targetAsset.value !== 'string' || !targetAsset.value.trim()) {
            setAssignError('Cannot assign equipment types: asset value is missing')
            return
        }
        setAssignSaving(true)
        setAssignError(null)
        try {
            await ebayTemplatesApi.updateFieldAsset(localField.id, assignAssetId, {
                value: targetAsset.value,
                name: targetAsset.name,
                is_default_fallback: Boolean(targetAsset.is_default_fallback),
                equipment_type_ids: assignEquipmentTypeIds,
            })
            await refreshFieldAssets()
            closeAssignDialog()
        } catch (err: any) {
            setAssignError(err.response?.data?.detail || 'Failed to assign equipment types')
        } finally {
            setAssignSaving(false)
        }
    }

    const isParentPatternFallbackBlank = parentPatternIsFallback && !parentPatternValueDraft.trim()
    const isVariationPatternFallbackBlank = variationPatternIsFallback && !variationPatternValueDraft.trim()
    const globalDescriptionAsset = descriptionAssets.find((a) => a.is_default_fallback)
    const effectiveGlobalDescriptionValue = descriptionIsFallback
        ? descriptionValueDraft
        : (globalDescriptionAsset?.value || '')
    const isGlobalDescriptionBlank = !String(effectiveGlobalDescriptionValue || '').trim()
    const descriptionGuidanceText = isGlobalDescriptionBlank
        ? 'Global is blank. Export will fail for any equipment type that does not have a specific description assigned.'
        : (
            descriptionSelectionMode === 'EQUIPMENT_TYPE_PRIMARY'
                ? 'Specific equipment-type descriptions will be used when assigned; otherwise Global will be used.'
                : 'Global description will be used for all equipment types unless you switch the selection mode.'
        )
    const globalDescriptionAssets = descriptionAssets.filter((entry) => entry.is_default_fallback === true)
    const assignedDescriptionAssets = descriptionAssets.filter(
        (entry) => entry.is_default_fallback !== true && (entry.equipment_type_ids || []).length > 0
    )
    const unassignedDescriptionAssets = descriptionAssets.filter(
        (entry) => entry.is_default_fallback !== true && (entry.equipment_type_ids || []).length === 0
    )
    const globalParentPatternAssets = parentPatternAssets.filter((entry) => entry.is_default_fallback === true)
    const assignedParentPatternAssets = parentPatternAssets.filter(
        (entry) => entry.is_default_fallback !== true && (entry.equipment_type_ids || []).length > 0
    )
    const unassignedParentPatternAssets = parentPatternAssets.filter(
        (entry) => entry.is_default_fallback !== true && (entry.equipment_type_ids || []).length === 0
    )
    const globalVariationPatternAssets = variationPatternAssets.filter((entry) => entry.is_default_fallback === true)
    const assignedVariationPatternAssets = variationPatternAssets.filter(
        (entry) => entry.is_default_fallback !== true && (entry.equipment_type_ids || []).length > 0
    )
    const unassignedVariationPatternAssets = variationPatternAssets.filter(
        (entry) => entry.is_default_fallback !== true && (entry.equipment_type_ids || []).length === 0
    )

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="h6">{localField.field_name}</Typography>
                    <IconButton size="small" onClick={onClose}>
                        <CloseIcon />
                    </IconButton>
                </Box>
                <Typography variant="caption" color="text.secondary">
                    Order Index: {localField.order_index} | ID: {localField.id}
                </Typography>
            </DialogTitle>
            <DialogContent dividers>
                <Stack spacing={3}>
                    {error && (
                        <Alert severity="error" onClose={() => setError(null)}>
                            {error}
                        </Alert>
                    )}

                    {/* Required Toggle */}
                    <Box>
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={localField.required}
                                    onChange={(e) => handleRequiredToggle(e.target.checked)}
                                    disabled={saving}
                                />
                            }
                            label="Required"
                        />
                        {saving && (
                            <Typography variant="caption" display="block" color="primary" sx={{ ml: 4 }}>
                                Saving...
                            </Typography>
                        )}
                    </Box>

                    {!isAssetManagedField(localField) && (
                        <>
                            {getRowScopeValue(localField) === 'both' ? (
                                <Stack spacing={1.5}>
                                    <TextField
                                        label="Parent Selected Value"
                                        fullWidth
                                        value={localField.parent_selected_value || ""}
                                        InputProps={{ readOnly: true }}
                                        disabled={saving}
                                        placeholder="(unset)"
                                        helperText="Select Parent value using chips below"
                                    />
                                    <TextField
                                        label="Parent Custom Value"
                                        fullWidth
                                        value={parentCustomDraft}
                                        disabled={saving}
                                        onChange={(e) => setParentCustomDraft(e.target.value)}
                                        onBlur={saveParentCustomDraft}
                                        helperText="Leave blank to clear"
                                    />
                                    <TextField
                                        label="Variation Selected Value"
                                        fullWidth
                                        value={localField.variation_selected_value || ""}
                                        InputProps={{ readOnly: true }}
                                        disabled={saving}
                                        placeholder="(unset)"
                                        helperText="Select Variation value using chips below"
                                    />
                                    <TextField
                                        label="Variation Custom Value"
                                        fullWidth
                                        value={variationCustomDraft}
                                        disabled={saving}
                                        onChange={(e) => setVariationCustomDraft(e.target.value)}
                                        onBlur={saveVariationCustomDraft}
                                        helperText="Leave blank to clear"
                                    />
                                </Stack>
                            ) : (
                                <TextField
                                    label="Default / Selected Value"
                                    fullWidth
                                    value={localField.selected_value || ""}
                                    InputProps={{ readOnly: true }}
                                    disabled={saving}
                                    placeholder="(unset)"
                                    helperText="Click a chip below to select a value"
                                />
                            )}

                            <ValidValuesSection
                                values={localField.allowed_values}
                                valuesDetailed={localField.allowed_values_detailed}
                                rowScope={getRowScopeValue(localField)}
                                selectedValue={localField.selected_value}
                                parentSelectedValue={localField.parent_selected_value}
                                variationSelectedValue={localField.variation_selected_value}
                                onChipClick={handleChipClick}
                                onParentChipClick={handleParentChipClick}
                                onVariationChipClick={handleVariationChipClick}
                                onDeleteValue={handleDeleteValue}
                                newValue={newValue}
                                onNewValueChange={setNewValue}
                                onAddValue={handleAddValue}
                                savingAdd={savingAdd}
                            />
                        </>
                    )}

                    {isDescriptionField(localField.field_name) && (
                        <Box>
                            <Typography variant="subtitle2" gutterBottom>
                                Equipment Type Descriptions
                            </Typography>
                            <Stack spacing={1.5}>
                                <FormControlLabel
                                    control={
                                        <Switch
                                            checked={descriptionIsFallback}
                                            onChange={(e) => {
                                                const checked = e.target.checked
                                                setDescriptionIsFallback(checked)
                                                if (checked) setDescriptionEquipmentTypeIds([])
                                            }}
                                            disabled={assetsLoading || assetsSaving}
                                        />
                                    }
                                    label="Global (all equipment types)"
                                />
                                <FormControl size="small" fullWidth disabled={descriptionIsFallback || assetsLoading || assetsSaving}>
                                    <Select
                                        multiple
                                        value={descriptionEquipmentTypeIds}
                                        onChange={(e) => setDescriptionEquipmentTypeIds((e.target.value as number[]))}
                                        renderValue={(selected) =>
                                            (selected as number[]).map((id) => equipmentTypeName(id)).join(', ')
                                        }
                                    >
                                        {equipmentTypes.map((et) => (
                                            <MenuItem key={et.id} value={et.id}>
                                                {et.name}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                                <Alert severity={isGlobalDescriptionBlank ? 'warning' : 'info'}>
                                    {descriptionGuidanceText}
                                </Alert>
                                <TextField
                                    label="Name"
                                    value={descriptionNameDraft}
                                    onChange={(e) => setDescriptionNameDraft(e.target.value)}
                                    disabled={assetsLoading || assetsSaving}
                                    helperText="Required when creating a new description asset."
                                />
                                <TextField
                                    label="HTML Description"
                                    multiline
                                    minRows={6}
                                    value={descriptionValueDraft}
                                    onChange={(e) => setDescriptionValueDraft(e.target.value)}
                                    disabled={assetsLoading || assetsSaving}
                                    helperText='Supports placeholders like [Manufacturer_Name], [Series_Name], [Model_Name], [Equipment_Type_Name], [Width], [Depth], [Height], [SKU].'
                                />
                                <Button
                                    variant="contained"
                                    onClick={handleSaveDescriptionAsset}
                                    disabled={
                                        assetsLoading
                                        || assetsSaving
                                        || (!descriptionIsFallback && !descriptionValueDraft.trim())
                                        || (!descriptionAssetId && !descriptionNameDraft.trim())
                                    }
                                >
                                    {assetsSaving ? 'Saving...' : (descriptionAssetId ? 'Update Description Asset' : 'Create Description Asset')}
                                </Button>
                                <Stack spacing={1}>
                                    {globalDescriptionAssets.length > 0 && (
                                        <>
                                            <Typography variant="subtitle2">Global (all equipment types)</Typography>
                                            {globalDescriptionAssets.map((entry) => (
                                                <Paper key={entry.id} variant="outlined" sx={{ p: 1.25 }}>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                                                        <Box sx={{ minWidth: 0 }}>
                                                            <Typography
                                                                variant="body1"
                                                                fontWeight={700}
                                                                sx={{ cursor: 'pointer' }}
                                                                onClick={() => beginEditAsset(entry)}
                                                            >
                                                                {entry.name || `Untitled (id: ${entry.id})`}
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                                                Global (all equipment types)
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
                                                                {(entry.value || '').slice(0, 140)}{(entry.value || '').length > 140 ? '...' : ''}
                                                            </Typography>
                                                        </Box>
                                                        <Stack direction="row" spacing={0.5}>
                                                            <Button size="small" onClick={() => beginEditAsset(entry)} disabled={assetsLoading || assetsSaving}>
                                                                Edit
                                                            </Button>
                                                            <IconButton size="small" onClick={() => handleDeleteAsset(entry.id)} disabled={assetsLoading || assetsSaving}>
                                                                <DeleteOutlineIcon fontSize="small" />
                                                            </IconButton>
                                                        </Stack>
                                                    </Box>
                                                </Paper>
                                            ))}
                                        </>
                                    )}
                                    {assignedDescriptionAssets.length > 0 && (
                                        <>
                                            <Typography variant="subtitle2">Assigned equipment types</Typography>
                                            {assignedDescriptionAssets.map((entry) => (
                                                <Paper key={entry.id} variant="outlined" sx={{ p: 1.25 }}>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                                                        <Box sx={{ minWidth: 0 }}>
                                                            <Typography
                                                                variant="body1"
                                                                fontWeight={700}
                                                                sx={{ cursor: 'pointer' }}
                                                                onClick={() => beginEditAsset(entry)}
                                                            >
                                                                {entry.name || `Untitled (id: ${entry.id})`}
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                                                Assigned: {(entry.equipment_type_ids || []).map((equipmentTypeId) => equipmentTypeName(equipmentTypeId)).join(', ')}
                                                            </Typography>
                                                            <Stack direction="row" flexWrap="wrap" gap={0.5} sx={{ mb: 0.5 }}>
                                                                {(entry.equipment_type_ids || []).map((equipmentTypeId) => (
                                                                    <Chip key={`${entry.id}-${equipmentTypeId}`} size="small" label={equipmentTypeName(equipmentTypeId)} />
                                                                ))}
                                                            </Stack>
                                                            <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
                                                                {(entry.value || '').slice(0, 140)}{(entry.value || '').length > 140 ? '...' : ''}
                                                            </Typography>
                                                        </Box>
                                                        <Stack direction="row" spacing={0.5}>
                                                            <Stack spacing={0.5}>
                                                                <Button size="small" onClick={() => beginEditAsset(entry)} disabled={assetsLoading || assetsSaving || assignSaving}>
                                                                    Edit
                                                                </Button>
                                                                <Button size="small" onClick={() => openAssignDialog(entry)} disabled={assetsLoading || assetsSaving || assignSaving}>
                                                                    Assign equipment types
                                                                </Button>
                                                            </Stack>
                                                            <IconButton size="small" onClick={() => handleDeleteAsset(entry.id)} disabled={assetsLoading || assetsSaving}>
                                                                <DeleteOutlineIcon fontSize="small" />
                                                            </IconButton>
                                                        </Stack>
                                                    </Box>
                                                </Paper>
                                            ))}
                                        </>
                                    )}
                                    {unassignedDescriptionAssets.length > 0 && (
                                        <>
                                            <Typography variant="subtitle2">Unassigned</Typography>
                                            {unassignedDescriptionAssets.map((entry) => (
                                                <Paper key={entry.id} variant="outlined" sx={{ p: 1.25 }}>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                                                        <Box sx={{ minWidth: 0 }}>
                                                            <Typography
                                                                variant="body1"
                                                                fontWeight={700}
                                                                sx={{ cursor: 'pointer' }}
                                                                onClick={() => beginEditAsset(entry)}
                                                            >
                                                                {entry.name || `Untitled (id: ${entry.id})`}
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                                                Assigned: (none)
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
                                                                {(entry.value || '').slice(0, 140)}{(entry.value || '').length > 140 ? '...' : ''}
                                                            </Typography>
                                                        </Box>
                                                        <Stack direction="row" spacing={0.5} alignItems="flex-start">
                                                            <Stack spacing={0.5}>
                                                                <Button size="small" onClick={() => beginEditAsset(entry)} disabled={assetsLoading || assetsSaving || assignSaving}>
                                                                    Edit
                                                                </Button>
                                                                <Button size="small" onClick={() => openAssignDialog(entry)} disabled={assetsLoading || assetsSaving || assignSaving}>
                                                                    Assign equipment types
                                                                </Button>
                                                            </Stack>
                                                            <IconButton size="small" onClick={() => handleDeleteAsset(entry.id)} disabled={assetsLoading || assetsSaving}>
                                                                <DeleteOutlineIcon fontSize="small" />
                                                            </IconButton>
                                                        </Stack>
                                                    </Box>
                                                </Paper>
                                            ))}
                                        </>
                                    )}
                                    {descriptionAssets.length === 0 && (
                                        <Typography variant="caption" color="text.secondary">
                                            No description assets saved yet.
                                        </Typography>
                                    )}
                                </Stack>
                            </Stack>
                        </Box>
                    )}

                    {isImageUrlField(localField.field_name) && (
                        <Box>
                            <Typography variant="subtitle2" gutterBottom>
                                Equipment Type Image URL Patterns
                            </Typography>
                            <Stack spacing={1.5}>
                                <Typography variant="subtitle2">Parent Image Pattern Assets</Typography>
                                <FormControlLabel
                                    control={
                                        <Switch
                                            checked={parentPatternIsFallback}
                                            onChange={(e) => {
                                                const checked = e.target.checked
                                                setParentPatternIsFallback(checked)
                                                if (checked) setParentPatternEquipmentTypeIds([])
                                            }}
                                            disabled={assetsLoading || assetsSaving}
                                        />
                                    }
                                    label="Global (all equipment types)"
                                />
                                <FormControl size="small" fullWidth disabled={parentPatternIsFallback || assetsLoading || assetsSaving}>
                                    <Select
                                        multiple
                                        value={parentPatternEquipmentTypeIds}
                                        onChange={(e) => setParentPatternEquipmentTypeIds((e.target.value as number[]))}
                                        renderValue={(selected) =>
                                            (selected as number[]).map((id) => equipmentTypeName(id)).join(', ')
                                        }
                                    >
                                        {equipmentTypes.map((et) => (
                                            <MenuItem key={et.id} value={et.id}>
                                                {et.name}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                                <TextField
                                    label="Name"
                                    value={parentPatternNameDraft}
                                    onChange={(e) => setParentPatternNameDraft(e.target.value)}
                                    disabled={assetsLoading || assetsSaving}
                                    helperText="Required when creating a new parent pattern asset."
                                />
                                <TextField
                                    label="Image Value Separator"
                                    value={parentPatternSeparatorDraft}
                                    onChange={(e) => setParentPatternSeparatorDraft((e.target.value || '').charAt(0) || '')}
                                    onBlur={() => { void handleSaveImageFieldSettings() }}
                                    disabled={assetsLoading || assetsSaving}
                                    helperText='Single character used to join expanded image URLs (default: |).'
                                />
                                <TextField
                                    label="Parent Pattern"
                                    multiline
                                    minRows={3}
                                    value={parentPatternValueDraft}
                                    onChange={(e) => setParentPatternValueDraft(e.target.value)}
                                    disabled={assetsLoading || assetsSaving}
                                    error={isParentPatternFallbackBlank}
                                    helperText='Use [INDEX] (or [IMAGE_INDEX]) for 001..012. Supports template tokens like [Model_Name], [Series_Name], [Manufacturer_Name].'
                                />
                                <Button
                                    variant="contained"
                                    onClick={() => handleSaveImagePatternAsset('image_parent_pattern')}
                                    disabled={
                                        assetsLoading
                                        || assetsSaving
                                        || !parentPatternValueDraft.trim()
                                        || isParentPatternFallbackBlank
                                        || (!parentPatternAssetId && !parentPatternNameDraft.trim())
                                    }
                                >
                                    {assetsSaving ? 'Saving...' : (parentPatternAssetId ? 'Update Parent Pattern Asset' : 'Create Parent Pattern Asset')}
                                </Button>
                                <Stack spacing={1}>
                                    {globalParentPatternAssets.length > 0 && (
                                        <>
                                            <Typography variant="subtitle2">Global (all equipment types)</Typography>
                                            {globalParentPatternAssets.map((entry) => (
                                                <Paper key={entry.id} variant="outlined" sx={{ p: 1.25 }}>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                                                        <Box sx={{ minWidth: 0 }}>
                                                            <Typography variant="body1" fontWeight={700} sx={{ cursor: 'pointer' }} onClick={() => beginEditAsset(entry)}>
                                                                {entry.name || `Untitled (id: ${entry.id})`}
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                                                Global (all equipment types)
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
                                                                {parseImagePatternMetadata(entry.value || '').pattern.slice(0, 140)}{parseImagePatternMetadata(entry.value || '').pattern.length > 140 ? '...' : ''}
                                                            </Typography>
                                                        </Box>
                                                        <Stack direction="row" spacing={0.5}>
                                                            <Button size="small" onClick={() => beginEditAsset(entry)} disabled={assetsLoading || assetsSaving}>
                                                                Edit
                                                            </Button>
                                                            <IconButton size="small" onClick={() => handleDeleteAsset(entry.id)} disabled={assetsLoading || assetsSaving}>
                                                                <DeleteOutlineIcon fontSize="small" />
                                                            </IconButton>
                                                        </Stack>
                                                    </Box>
                                                </Paper>
                                            ))}
                                        </>
                                    )}
                                    {assignedParentPatternAssets.length > 0 && (
                                        <>
                                            <Typography variant="subtitle2">Assigned equipment types</Typography>
                                            {assignedParentPatternAssets.map((entry) => (
                                                <Paper key={entry.id} variant="outlined" sx={{ p: 1.25 }}>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                                                        <Box sx={{ minWidth: 0 }}>
                                                            <Typography variant="body1" fontWeight={700} sx={{ cursor: 'pointer' }} onClick={() => beginEditAsset(entry)}>
                                                                {entry.name || `Untitled (id: ${entry.id})`}
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                                                Assigned: {(entry.equipment_type_ids || []).map((equipmentTypeId) => equipmentTypeName(equipmentTypeId)).join(', ')}
                                                            </Typography>
                                                            <Stack direction="row" flexWrap="wrap" gap={0.5} sx={{ mb: 0.5 }}>
                                                                {(entry.equipment_type_ids || []).map((equipmentTypeId) => (
                                                                    <Chip key={`${entry.id}-${equipmentTypeId}`} size="small" label={equipmentTypeName(equipmentTypeId)} />
                                                                ))}
                                                            </Stack>
                                                            <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
                                                                {parseImagePatternMetadata(entry.value || '').pattern.slice(0, 140)}{parseImagePatternMetadata(entry.value || '').pattern.length > 140 ? '...' : ''}
                                                            </Typography>
                                                        </Box>
                                                        <Stack direction="row" spacing={0.5}>
                                                            <Stack spacing={0.5}>
                                                                <Button size="small" onClick={() => beginEditAsset(entry)} disabled={assetsLoading || assetsSaving || assignSaving}>
                                                                    Edit
                                                                </Button>
                                                                <Button size="small" onClick={() => openAssignDialog(entry)} disabled={assetsLoading || assetsSaving || assignSaving}>
                                                                    Assign equipment types
                                                                </Button>
                                                            </Stack>
                                                            <IconButton size="small" onClick={() => handleDeleteAsset(entry.id)} disabled={assetsLoading || assetsSaving}>
                                                                <DeleteOutlineIcon fontSize="small" />
                                                            </IconButton>
                                                        </Stack>
                                                    </Box>
                                                </Paper>
                                            ))}
                                        </>
                                    )}
                                    {unassignedParentPatternAssets.length > 0 && (
                                        <>
                                            <Typography variant="subtitle2">Unassigned</Typography>
                                            {unassignedParentPatternAssets.map((entry) => (
                                                <Paper key={entry.id} variant="outlined" sx={{ p: 1.25 }}>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                                                        <Box sx={{ minWidth: 0 }}>
                                                            <Typography variant="body1" fontWeight={700} sx={{ cursor: 'pointer' }} onClick={() => beginEditAsset(entry)}>
                                                                {entry.name || `Untitled (id: ${entry.id})`}
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                                                Assigned: (none)
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
                                                                {parseImagePatternMetadata(entry.value || '').pattern.slice(0, 140)}{parseImagePatternMetadata(entry.value || '').pattern.length > 140 ? '...' : ''}
                                                            </Typography>
                                                        </Box>
                                                        <Stack direction="row" spacing={0.5} alignItems="flex-start">
                                                            <Stack spacing={0.5}>
                                                                <Button size="small" onClick={() => beginEditAsset(entry)} disabled={assetsLoading || assetsSaving || assignSaving}>
                                                                    Edit
                                                                </Button>
                                                                <Button size="small" onClick={() => openAssignDialog(entry)} disabled={assetsLoading || assetsSaving || assignSaving}>
                                                                    Assign equipment types
                                                                </Button>
                                                            </Stack>
                                                            <IconButton size="small" onClick={() => handleDeleteAsset(entry.id)} disabled={assetsLoading || assetsSaving}>
                                                                <DeleteOutlineIcon fontSize="small" />
                                                            </IconButton>
                                                        </Stack>
                                                    </Box>
                                                </Paper>
                                            ))}
                                        </>
                                    )}
                                    {parentPatternAssets.length === 0 && (
                                        <Typography variant="caption" color="text.secondary">
                                            No parent image pattern assets saved yet.
                                        </Typography>
                                    )}
                                </Stack>

                                <Typography variant="subtitle2">Variation Image Pattern Assets</Typography>
                                <FormControlLabel
                                    control={
                                        <Switch
                                            checked={variationPatternIsFallback}
                                            onChange={(e) => {
                                                const checked = e.target.checked
                                                setVariationPatternIsFallback(checked)
                                                if (checked) setVariationPatternEquipmentTypeIds([])
                                            }}
                                            disabled={assetsLoading || assetsSaving}
                                        />
                                    }
                                    label="Global (all equipment types)"
                                />
                                <FormControl size="small" fullWidth disabled={variationPatternIsFallback || assetsLoading || assetsSaving}>
                                    <Select
                                        multiple
                                        value={variationPatternEquipmentTypeIds}
                                        onChange={(e) => setVariationPatternEquipmentTypeIds((e.target.value as number[]))}
                                        renderValue={(selected) =>
                                            (selected as number[]).map((id) => equipmentTypeName(id)).join(', ')
                                        }
                                    >
                                        {equipmentTypes.map((et) => (
                                            <MenuItem key={et.id} value={et.id}>
                                                {et.name}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                                <TextField
                                    label="Name"
                                    value={variationPatternNameDraft}
                                    onChange={(e) => setVariationPatternNameDraft(e.target.value)}
                                    disabled={assetsLoading || assetsSaving}
                                    helperText="Required when creating a new variation pattern asset."
                                />
                                <TextField
                                    label="Image Value Separator"
                                    value={variationPatternSeparatorDraft}
                                    onChange={(e) => setVariationPatternSeparatorDraft((e.target.value || '').charAt(0) || '')}
                                    onBlur={() => { void handleSaveImageFieldSettings() }}
                                    disabled={assetsLoading || assetsSaving}
                                    helperText='Single character used to join expanded image URLs (default: |).'
                                />
                                <TextField
                                    label="Variation Prefix Pattern"
                                    value={variationPatternPrefixDraft}
                                    onChange={(e) => setVariationPatternPrefixDraft(e.target.value)}
                                    onBlur={() => { void handleSaveImageFieldSettings() }}
                                    disabled={assetsLoading || assetsSaving}
                                    helperText='Optional prefix for variation image URLs. Supports [COLOR_FRIENDLY_NAME], [COLOR_ABBR], [COLOR_SKU].'
                                />
                                <Button
                                    variant="outlined"
                                    onClick={handleSaveImageFieldSettings}
                                    disabled={assetsLoading || assetsSaving || (parentPatternAssets.length + variationPatternAssets.length) === 0}
                                >
                                    {assetsSaving ? 'Saving...' : 'Save Image URL Field Settings'}
                                </Button>
                                <TextField
                                    label="Variation Pattern"
                                    multiline
                                    minRows={3}
                                    value={variationPatternValueDraft}
                                    onChange={(e) => setVariationPatternValueDraft(e.target.value)}
                                    disabled={assetsLoading || assetsSaving}
                                    error={isVariationPatternFallbackBlank}
                                    helperText='Must include [COLOR_SKU] and [INDEX] (or [IMAGE_INDEX]) for 001..012.'
                                />
                                <Button
                                    variant="contained"
                                    onClick={() => handleSaveImagePatternAsset('image_variation_pattern')}
                                    disabled={
                                        assetsLoading
                                        || assetsSaving
                                        || !variationPatternValueDraft.trim()
                                        || isVariationPatternFallbackBlank
                                        || (!variationPatternAssetId && !variationPatternNameDraft.trim())
                                    }
                                >
                                    {assetsSaving ? 'Saving...' : (variationPatternAssetId ? 'Update Variation Pattern Asset' : 'Create Variation Pattern Asset')}
                                </Button>
                                <Stack spacing={1}>
                                    {globalVariationPatternAssets.length > 0 && (
                                        <>
                                            <Typography variant="subtitle2">Global (all equipment types)</Typography>
                                            {globalVariationPatternAssets.map((entry) => (
                                                <Paper key={entry.id} variant="outlined" sx={{ p: 1.25 }}>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                                                        <Box sx={{ minWidth: 0 }}>
                                                            <Typography variant="body1" fontWeight={700} sx={{ cursor: 'pointer' }} onClick={() => beginEditAsset(entry)}>
                                                                {entry.name || `Untitled (id: ${entry.id})`}
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                                                Global (all equipment types)
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
                                                                {parseImagePatternMetadata(entry.value || '').pattern.slice(0, 140)}{parseImagePatternMetadata(entry.value || '').pattern.length > 140 ? '...' : ''}
                                                            </Typography>
                                                        </Box>
                                                        <Stack direction="row" spacing={0.5}>
                                                            <Button size="small" onClick={() => beginEditAsset(entry)} disabled={assetsLoading || assetsSaving}>
                                                                Edit
                                                            </Button>
                                                            <IconButton size="small" onClick={() => handleDeleteAsset(entry.id)} disabled={assetsLoading || assetsSaving}>
                                                                <DeleteOutlineIcon fontSize="small" />
                                                            </IconButton>
                                                        </Stack>
                                                    </Box>
                                                </Paper>
                                            ))}
                                        </>
                                    )}
                                    {assignedVariationPatternAssets.length > 0 && (
                                        <>
                                            <Typography variant="subtitle2">Assigned equipment types</Typography>
                                            {assignedVariationPatternAssets.map((entry) => (
                                                <Paper key={entry.id} variant="outlined" sx={{ p: 1.25 }}>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                                                        <Box sx={{ minWidth: 0 }}>
                                                            <Typography variant="body1" fontWeight={700} sx={{ cursor: 'pointer' }} onClick={() => beginEditAsset(entry)}>
                                                                {entry.name || `Untitled (id: ${entry.id})`}
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                                                Assigned: {(entry.equipment_type_ids || []).map((equipmentTypeId) => equipmentTypeName(equipmentTypeId)).join(', ')}
                                                            </Typography>
                                                            <Stack direction="row" flexWrap="wrap" gap={0.5} sx={{ mb: 0.5 }}>
                                                                {(entry.equipment_type_ids || []).map((equipmentTypeId) => (
                                                                    <Chip key={`${entry.id}-${equipmentTypeId}`} size="small" label={equipmentTypeName(equipmentTypeId)} />
                                                                ))}
                                                            </Stack>
                                                            <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
                                                                {parseImagePatternMetadata(entry.value || '').pattern.slice(0, 140)}{parseImagePatternMetadata(entry.value || '').pattern.length > 140 ? '...' : ''}
                                                            </Typography>
                                                        </Box>
                                                        <Stack direction="row" spacing={0.5}>
                                                            <Stack spacing={0.5}>
                                                                <Button size="small" onClick={() => beginEditAsset(entry)} disabled={assetsLoading || assetsSaving || assignSaving}>
                                                                    Edit
                                                                </Button>
                                                                <Button size="small" onClick={() => openAssignDialog(entry)} disabled={assetsLoading || assetsSaving || assignSaving}>
                                                                    Assign equipment types
                                                                </Button>
                                                            </Stack>
                                                            <IconButton size="small" onClick={() => handleDeleteAsset(entry.id)} disabled={assetsLoading || assetsSaving}>
                                                                <DeleteOutlineIcon fontSize="small" />
                                                            </IconButton>
                                                        </Stack>
                                                    </Box>
                                                </Paper>
                                            ))}
                                        </>
                                    )}
                                    {unassignedVariationPatternAssets.length > 0 && (
                                        <>
                                            <Typography variant="subtitle2">Unassigned</Typography>
                                            {unassignedVariationPatternAssets.map((entry) => (
                                                <Paper key={entry.id} variant="outlined" sx={{ p: 1.25 }}>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                                                        <Box sx={{ minWidth: 0 }}>
                                                            <Typography variant="body1" fontWeight={700} sx={{ cursor: 'pointer' }} onClick={() => beginEditAsset(entry)}>
                                                                {entry.name || `Untitled (id: ${entry.id})`}
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                                                Assigned: (none)
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
                                                                {parseImagePatternMetadata(entry.value || '').pattern.slice(0, 140)}{parseImagePatternMetadata(entry.value || '').pattern.length > 140 ? '...' : ''}
                                                            </Typography>
                                                        </Box>
                                                        <Stack direction="row" spacing={0.5} alignItems="flex-start">
                                                            <Stack spacing={0.5}>
                                                                <Button size="small" onClick={() => beginEditAsset(entry)} disabled={assetsLoading || assetsSaving || assignSaving}>
                                                                    Edit
                                                                </Button>
                                                                <Button size="small" onClick={() => openAssignDialog(entry)} disabled={assetsLoading || assetsSaving || assignSaving}>
                                                                    Assign equipment types
                                                                </Button>
                                                            </Stack>
                                                            <IconButton size="small" onClick={() => handleDeleteAsset(entry.id)} disabled={assetsLoading || assetsSaving}>
                                                                <DeleteOutlineIcon fontSize="small" />
                                                            </IconButton>
                                                        </Stack>
                                                    </Box>
                                                </Paper>
                                            ))}
                                        </>
                                    )}
                                    {variationPatternAssets.length === 0 && (
                                        <Typography variant="caption" color="text.secondary">
                                            No variation image pattern assets saved yet.
                                        </Typography>
                                    )}
                                </Stack>
                            </Stack>
                        </Box>
                    )}
                </Stack>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Close</Button>
            </DialogActions>

            <Dialog open={assignDialogOpen} onClose={closeAssignDialog} maxWidth="xs" fullWidth>
                <DialogTitle>Assign equipment types</DialogTitle>
                <DialogContent dividers>
                    <Stack spacing={1.5}>
                        <FormControl size="small" fullWidth>
                            <Select
                                multiple
                                value={assignEquipmentTypeIds}
                                onChange={(e) => {
                                    setAssignEquipmentTypeIds(e.target.value as number[])
                                    if (assignError) setAssignError(null)
                                }}
                                renderValue={(selected) =>
                                    (selected as number[]).map((id) => equipmentTypeName(id)).join(', ')
                                }
                            >
                                {equipmentTypes.map((et) => (
                                    <MenuItem key={et.id} value={et.id}>
                                        {et.name}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        {assignError && (
                            <Typography variant="caption" color="error">
                                {assignError}
                            </Typography>
                        )}
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeAssignDialog} disabled={assignSaving}>Cancel</Button>
                    <Button variant="contained" onClick={handleSaveAssignments} disabled={assignSaving}>
                        {assignSaving ? 'Saving...' : 'Save assignments'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Dialog>
    )
}

// --- Main Page Component ---
export default function EbayTemplatesPage() {
    const [currentTemplate, setCurrentTemplate] = useState<EbayTemplateResponse | null>(null)
    const [parsedFields, setParsedFields] = useState<EbayFieldResponse[]>([])
    const [parseSummary, setParseSummary] = useState<EbayTemplateParseSummary | null>(null)
    const [selectedField, setSelectedField] = useState<EbayFieldResponse | null>(null)
    const [modalOpen, setModalOpen] = useState(false)

    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [successMsg, setSuccessMsg] = useState<string | null>(null)
    const [savingRequiredById, setSavingRequiredById] = useState<Record<number, boolean>>({})
    const [savingRowScopeById, setSavingRowScopeById] = useState<Record<number, boolean>>({})

    const [previewOpen, setPreviewOpen] = useState(false)
    const [previewLoading, setPreviewLoading] = useState(false)
    const [previewError, setPreviewError] = useState<string | null>(null)
    const [previewData, setPreviewData] = useState<EbayTemplatePreviewResponse | null>(null)

    const [integrityData, setIntegrityData] = useState<EbayTemplateIntegrityResponse | null>(null)
    const [integrityLoading, setIntegrityLoading] = useState(false)

    const [verificationData, setVerificationData] = useState<EbayTemplateVerificationResponse | null>(null)
    const [verificationLoading, setVerificationLoading] = useState(false)
    const [scanResult, setScanResult] = useState<EbayTemplateScanResponse | null>(null)
    const [scanLoading, setScanLoading] = useState(false)
    const [headerRowOverrideInput, setHeaderRowOverrideInput] = useState('')
    const [firstDataRowOverrideInput, setFirstDataRowOverrideInput] = useState('')
    const [autoScanPending, setAutoScanPending] = useState(false)

    const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null)
    const [snackbarMessage, setSnackbarMessage] = useState<string | null>(null)

    const parseOptionalPositiveInt = (raw: string): number | -1 | undefined => {
        const trimmed = raw.trim()
        if (!trimmed) return undefined
        const parsed = Number(trimmed)
        if (!Number.isInteger(parsed)) return -1
        return parsed
    }

    const headerOverrideParsed = parseOptionalPositiveInt(headerRowOverrideInput)
    const firstDataOverrideParsed = parseOptionalPositiveInt(firstDataRowOverrideInput)
    const hasInvalidOverride =
        headerOverrideParsed === -1 ||
        firstDataOverrideParsed === -1 ||
        (typeof headerOverrideParsed === 'number' && headerOverrideParsed <= 0) ||
        (typeof firstDataOverrideParsed === 'number' && firstDataOverrideParsed <= 0)

    const scanOverridePayload = (() => {
        const payload: { header_row_override?: number; first_data_row_override?: number } = {}
        if (typeof headerOverrideParsed === 'number' && headerOverrideParsed > 0) {
            payload.header_row_override = headerOverrideParsed
        }
        if (typeof firstDataOverrideParsed === 'number' && firstDataOverrideParsed > 0) {
            payload.first_data_row_override = firstDataOverrideParsed
        }
        return payload
    })()

    const loadCurrentTemplate = async () => {
        setLoading(true)
        setError(null)
        try {
            const tmpl = await ebayTemplatesApi.getCurrent()
            setCurrentTemplate(tmpl)

            if (tmpl) {
                try {
                    const fieldsResp = await ebayTemplatesApi.getFields(tmpl.id)
                    setParsedFields(fieldsResp.fields)
                } catch (e) {
                    setParsedFields([])
                }
            } else {
                setParsedFields([])
                setParseSummary(null)
            }
        } catch (err: any) {
            setError(`Failed to load current template: ${err.message || String(err)}`)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadCurrentTemplate()
    }, [])

    useEffect(() => {
        if (!modalOpen || !selectedField) return
        const matchedField = parsedFields.find((f) => f.id === selectedField.id)
        if (!matchedField) {
            setModalOpen(false)
            setSelectedField(null)
            return
        }
        setSelectedField(matchedField)
    }, [modalOpen, parsedFields, selectedField])

    useEffect(() => {
        const runAutoScan = async () => {
            if (!autoScanPending || !currentTemplate?.id) return
            try {
                const result = await ebayTemplatesApi.scan(currentTemplate.id, {})
                setScanResult(result)
                setSuccessMsg('Template scan completed.')
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Template scan failed')
            } finally {
                setAutoScanPending(false)
            }
        }
        runAutoScan()
    }, [autoScanPending, currentTemplate?.id])

    const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        if (!file) return

        if (!file.name.endsWith('.xlsx')) {
            setError("Please upload a .xlsx file")
            return
        }

        setLoading(true)
        setError(null)
        setSuccessMsg(null)

        try {
            setModalOpen(false)
            setSelectedField(null)
            const resp = await ebayTemplatesApi.upload(file)
            setCurrentTemplate(resp)
            try {
                const fieldsResp = await ebayTemplatesApi.getFields(resp.id)
                setParsedFields(fieldsResp.fields)
            } catch {
                setParsedFields([])
            }
            if (resp.template_unchanged) {
                setSuccessMsg(resp.message || "Template unchanged — no re-parse required.")
                setAutoScanPending(false)
            } else {
                setSuccessMsg("Template uploaded successfully.")
                setAutoScanPending(true)
            }
        } catch (err: any) {
            setError(`Upload failed: ${err.message || String(err)}`)
        } finally {
            setLoading(false)
            event.target.value = ''
        }
    }

    const handleParse = async () => {
        if (!currentTemplate) return

        setLoading(true)
        setError(null)
        setSuccessMsg(null)

        try {
            setModalOpen(false)
            setSelectedField(null)
            const summary = await ebayTemplatesApi.parse(currentTemplate.id)
            setParseSummary(summary)

            // Refetch to get fresh data
            const fieldsResp = await ebayTemplatesApi.getFields(currentTemplate.id)
            setParsedFields(fieldsResp.fields)

            setSuccessMsg("Template parsed successfully.")
        } catch (err: any) {
            setError(`Parse failed: ${err.message || String(err)}`)
        } finally {
            setLoading(false)
        }
    }

    const handleInlineRequiredToggle = async (fieldId: number, checked: boolean) => {
        // Set saving state for this field
        setSavingRequiredById(prev => ({ ...prev, [fieldId]: true }))

        try {
            const updated = await ebayTemplatesApi.updateField(fieldId, { required: checked })

            // Update parsedFields with the returned field
            setParsedFields(prev => prev.map(f => f.id === fieldId ? updated : f))

            // If the modal is open for this field, update selectedField too
            if (selectedField?.id === fieldId) {
                setSelectedField(updated)
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update required status')
            // No need to revert since we update on success only
        } finally {
            setSavingRequiredById(prev => ({ ...prev, [fieldId]: false }))
        }
    }

    const handleRowClick = (field: EbayFieldResponse) => {
        setSelectedField(field)
        setModalOpen(true)
    }

    const handleInlineRowScopeChange = async (fieldId: number, rowScope: EbayRowScope) => {
        setSavingRowScopeById(prev => ({ ...prev, [fieldId]: true }))
        try {
            const updated = await ebayTemplatesApi.updateField(fieldId, { row_scope: rowScope })
            setParsedFields(prev => prev.map(f => f.id === fieldId ? updated : f))
            if (selectedField?.id === fieldId) {
                setSelectedField(updated)
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update row scope')
        } finally {
            setSavingRowScopeById(prev => ({ ...prev, [fieldId]: false }))
        }
    }

    const handleScanTemplate = async () => {
        if (!currentTemplate || hasInvalidOverride) return
        setScanLoading(true)
        setError(null)
        try {
            const result = await ebayTemplatesApi.scan(currentTemplate.id, scanOverridePayload)
            setScanResult(result)
            setSuccessMsg('Template scan completed.')
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Template scan failed')
        } finally {
            setScanLoading(false)
        }
    }

    const handleParseUsingSettings = async () => {
        if (!currentTemplate || hasInvalidOverride) return
        setLoading(true)
        setError(null)
        setSuccessMsg(null)
        try {
            setModalOpen(false)
            setSelectedField(null)
            const summary = await ebayTemplatesApi.parse(currentTemplate.id, scanOverridePayload)
            setParseSummary(summary)
            const fieldsResp = await ebayTemplatesApi.getFields(currentTemplate.id)
            setParsedFields(fieldsResp.fields)
            setSuccessMsg('Template parsed successfully using selected scan settings.')
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Parse failed')
        } finally {
            setLoading(false)
        }
    }

    const handleResetToTemplateDefaults = async () => {
        if (!currentTemplate || hasInvalidOverride) return
        const confirmed = window.confirm(
            'Reset required, row scope, selected/custom values, and scoped values to template defaults for this parse?'
        )
        if (!confirmed) return

        setLoading(true)
        setError(null)
        setSuccessMsg(null)
        try {
            setModalOpen(false)
            setSelectedField(null)
            const summary = await ebayTemplatesApi.parse(currentTemplate.id, {
                ...scanOverridePayload,
                reset_to_template_defaults: true
            })
            setParseSummary(summary)
            const fieldsResp = await ebayTemplatesApi.getFields(currentTemplate.id)
            setParsedFields(fieldsResp.fields)
            setSuccessMsg('Template parsed and reset to template defaults.')
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Reset parse failed')
        } finally {
            setLoading(false)
        }
    }

    const handleOpenNativePreview = () => {
        setMenuAnchorEl(null)
        const url = ebayTemplatesApi.previewCurrentTemplateInlineUrl()
        const newWindow = window.open(url, '_blank', 'noopener,noreferrer')

        if (newWindow === null) {
            // Popup blocked - fallback to grid preview
            setSnackbarMessage('Popup blocked. Opening grid preview instead.')
            handleOpenGridPreview()
        } else {
            // Note: Most browsers will download XLSX files since they can't display them inline
            setSnackbarMessage('Opening template. Note: Your browser may download the file since XLSX cannot be displayed inline.')
        }
    }

    const handleOpenGridPreview = async () => {
        setMenuAnchorEl(null)
        setPreviewOpen(true)
        setPreviewLoading(true)
        setIntegrityLoading(true)
        setPreviewError(null)
        setPreviewData(null)
        setIntegrityData(null)

        try {
            // Fetch both in parallel
            const [previewResult, integrityResult] = await Promise.allSettled([
                ebayTemplatesApi.previewCurrentTemplate(),
                ebayTemplatesApi.getCurrentIntegrity()
            ])

            // Handle preview result
            if (previewResult.status === 'fulfilled') {
                setPreviewData(previewResult.value)
            } else {
                setPreviewError('Failed to load preview')
            }

            // Handle integrity result (don't fail if it errors)
            if (integrityResult.status === 'fulfilled') {
                setIntegrityData(integrityResult.value)
            }
        } catch (err: any) {
            setPreviewError(err.response?.data?.detail || 'Failed to load preview')
        } finally {
            setPreviewLoading(false)
            setIntegrityLoading(false)
        }
    }

    const triggerBlobDownload = (blob: Blob, filename: string) => {
        const url = URL.createObjectURL(blob)
        try {
            const anchor = document.createElement('a')
            anchor.href = url
            anchor.download = filename || 'ebay_template.xlsx'
            document.body.appendChild(anchor)
            anchor.click()
            document.body.removeChild(anchor)
        } finally {
            URL.revokeObjectURL(url)
        }
    }

    const handleDownloadXLSX = async () => {
        setMenuAnchorEl(null)
        try {
            const { blob, filename } = await ebayTemplatesApi.downloadCurrentTemplateBlob()
            triggerBlobDownload(blob, filename)
        } catch (err: any) {
            const status = err?.response?.status
            if (status === 401 || status === 403) {
                setError('Not authorized to download template')
            } else {
                setError(err?.response?.data?.detail || 'Failed to download template')
            }
        }
    }

    const handleDownloadTemplate = async () => {
        try {
            const { blob, filename } = await ebayTemplatesApi.downloadCurrentTemplateBlob()
            triggerBlobDownload(blob, filename)
        } catch (err: any) {
            const status = err?.response?.status
            if (status === 401 || status === 403) {
                setError('Not authorized to download template')
            } else {
                setError(err?.response?.data?.detail || 'Failed to download template')
            }
        }
    }

    const handleVerifyNow = async () => {
        setVerificationLoading(true)
        try {
            const result = await ebayTemplatesApi.getCurrentVerification()
            setVerificationData(result)
        } catch (err: any) {
            // Don't fail the whole modal - just show error in verification section
            console.error('Verification failed:', err)
        } finally {
            setVerificationLoading(false)
        }
    }

    return (
        <Box sx={{ p: 3, pt: 2, height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
            {/* Header / Top Bar */}
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="h5">eBay Templates</Typography>
                <Stack direction="row" spacing={2}>
                    {currentTemplate ? (
                        <Paper sx={{ px: 2, py: 0.5, display: 'flex', alignItems: 'center', gap: 2 }} variant="outlined">
                            <Box>
                                <Typography variant="caption" display="block" color="text.secondary">Current Template</Typography>
                                <Typography variant="body2" fontWeight="bold">{currentTemplate.original_filename}</Typography>
                            </Box>
                            <Divider orientation="vertical" flexItem />
                            <Box>
                                <Typography variant="caption" display="block" color="text.secondary">Uploaded</Typography>
                                <Typography variant="body2">{new Date(currentTemplate.uploaded_at || '').toLocaleDateString()}</Typography>
                            </Box>
                        </Paper>
                    ) : (
                        <Alert severity="info" sx={{ py: 0 }}>No template uploaded</Alert>
                    )}

                    <Button
                        variant="outlined"
                        startIcon={<RefreshIcon />}
                        onClick={loadCurrentTemplate}
                        disabled={loading}
                    >
                        Refresh
                    </Button>
                    <Button
                        component="label"
                        variant="outlined"
                        startIcon={<CloudUploadIcon />}
                        disabled={loading}
                    >
                        Upload
                        <input type="file" hidden accept=".xlsx" onChange={handleUpload} />
                    </Button>
                    <Button
                        variant="outlined"
                        startIcon={<DownloadIcon />}
                        onClick={handleDownloadTemplate}
                        disabled={!currentTemplate}
                    >
                        DOWNLOAD TEMPLATE
                    </Button>
                    <Button
                        variant="outlined"
                        startIcon={<VisibilityIcon />}
                        endIcon={<ArrowDropDownIcon />}
                        onClick={(e) => setMenuAnchorEl(e.currentTarget)}
                        disabled={!currentTemplate}
                    >
                        PREVIEW EXPORT
                    </Button>
                    <Menu
                        anchorEl={menuAnchorEl}
                        open={Boolean(menuAnchorEl)}
                        onClose={() => setMenuAnchorEl(null)}
                    >
                        <MenuItem onClick={handleOpenNativePreview}>
                            <VisibilityIcon sx={{ mr: 1 }} fontSize="small" />
                            Open in new tab (XLSX)
                        </MenuItem>
                        <MenuItem onClick={handleOpenGridPreview}>
                            <GridOnIcon sx={{ mr: 1 }} fontSize="small" />
                            Grid preview
                        </MenuItem>
                        <MenuItem onClick={handleDownloadXLSX}>
                            <DownloadIcon sx={{ mr: 1 }} fontSize="small" />
                            Download XLSX
                        </MenuItem>
                    </Menu>
                    <Button
                        variant="contained"
                        color="primary"
                        startIcon={<PlayArrowIcon />}
                        onClick={handleParse}
                        disabled={loading || !currentTemplate}
                    >
                        Parse
                    </Button>
                </Stack>
            </Stack>

            {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
            {successMsg && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMsg(null)}>{successMsg}</Alert>}

            {parseSummary && (
                <Alert severity="info" sx={{ mb: 2 }} icon={<CheckCircleIcon />}>
                    Parse Results: {parseSummary.fields_inserted} fields, {parseSummary.values_inserted} allowed values, {parseSummary.defaults_applied} defaults applied.
                </Alert>
            )}

            <Paper sx={{ p: 2, mb: 2 }} variant="outlined">
                <Typography variant="h6" sx={{ mb: 1 }}>Template Scan</Typography>
                <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 1.5 }}>
                    <TextField
                        size="small"
                        label="Header Row Override"
                        type="number"
                        value={headerRowOverrideInput}
                        onChange={(e) => setHeaderRowOverrideInput(e.target.value)}
                        helperText={hasInvalidOverride ? 'Use blank or positive integer values only.' : 'Excel 1-based row index. Leave blank to auto-detect.'}
                        error={hasInvalidOverride}
                    />
                    <TextField
                        size="small"
                        label="First Data Row Override"
                        type="number"
                        value={firstDataRowOverrideInput}
                        onChange={(e) => setFirstDataRowOverrideInput(e.target.value)}
                        helperText={hasInvalidOverride ? 'Use blank or positive integer values only.' : 'Excel 1-based row index. Leave blank to auto-detect.'}
                        error={hasInvalidOverride}
                    />
                    <Button
                        variant="outlined"
                        onClick={handleScanTemplate}
                        disabled={!currentTemplate || scanLoading || hasInvalidOverride}
                    >
                        {scanResult ? (scanLoading ? 'Rescanning...' : 'Rescan') : (scanLoading ? 'Scanning...' : 'Scan')}
                    </Button>
                    <Button
                        variant="contained"
                        onClick={handleParseUsingSettings}
                        disabled={!currentTemplate || loading || hasInvalidOverride}
                    >
                        {loading ? 'Parsing...' : 'Parse using these settings'}
                    </Button>
                    <Button
                        variant="outlined"
                        color="warning"
                        onClick={handleResetToTemplateDefaults}
                        disabled={!currentTemplate || loading || hasInvalidOverride}
                    >
                        {loading ? 'Resetting...' : 'Reset to template defaults'}
                    </Button>
                </Stack>
                {scanResult && (
                    <Stack spacing={0.75}>
                        <Typography variant="body2"><strong>Template Sheet:</strong> {scanResult.template_sheet_name}</Typography>
                        <Typography variant="body2"><strong>Valid Values Sheet:</strong> {scanResult.valid_values_sheet_name}</Typography>
                        <Typography variant="body2"><strong>Default Values Sheet:</strong> {scanResult.default_values_sheet_name}</Typography>
                        <Typography variant="body2"><strong>Detected Header Row:</strong> {scanResult.detected_header_row}</Typography>
                        <Typography variant="body2"><strong>Detected First Data Row:</strong> {scanResult.detected_first_data_row}</Typography>
                        <Typography variant="body2">
                            <strong>Header Detection Scores:</strong> base_non_empty={scanResult.header_detection_scores.base_non_empty}, match_known_fields={scanResult.header_detection_scores.match_known_fields}, scanned_rows={scanResult.header_detection_scores.scanned_rows}
                        </Typography>
                        <Typography variant="body2"><strong>Header Preview:</strong> {scanResult.header_preview.join(', ')}</Typography>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>
                            <strong>Reasons:</strong>{'\n'}{scanResult.reasons.join('\n')}
                        </Typography>
                    </Stack>
                )}
            </Paper>

            {/* Amazon-style Table Layout */}
            {parsedFields.length > 0 ? (
                <Paper sx={{ flex: 1, overflow: 'hidden' }} variant="outlined">
                    <TableContainer sx={{ height: '100%' }}>
                        <Table stickyHeader size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell sx={{ fontWeight: 'bold', width: '40%' }}>Field Name</TableCell>
                                    <TableCell align="center" sx={{ fontWeight: 'bold', width: '20%' }}>Required</TableCell>
                                    <TableCell sx={{ fontWeight: 'bold', width: '40%' }}>Default / Selected Value</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {parsedFields.map((field) => (
                                    <TableRow
                                        key={field.id}
                                        hover
                                        onClick={() => handleRowClick(field)}
                                        sx={{ cursor: 'pointer' }}
                                    >
                                        <TableCell sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
                                            {field.field_name}
                                        </TableCell>
                                        <TableCell align="center">
                                            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0.5 }}>
                                                <Switch
                                                    checked={field.required}
                                                    disabled={!!savingRequiredById[field.id]}
                                                    size="small"
                                                    color={field.required ? "primary" : "default"}
                                                    onClick={(e) => e.stopPropagation()}
                                                    onChange={(e) => handleInlineRequiredToggle(field.id, e.target.checked)}
                                                />
                                                {savingRequiredById[field.id] && (
                                                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                                                        Saving...
                                                    </Typography>
                                                )}
                                            </Box>
                                        </TableCell>
                                        <TableCell>
                                            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'stretch', gap: 0.75 }}>
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                    {(() => {
                                                    const valueCount = (field.allowed_values_detailed?.length ?? field.allowed_values?.length ?? 0)

                                                    if (valueCount === 0) {
                                                        return (
                                                            <Typography variant="caption" color="text.secondary">
                                                                (0)
                                                            </Typography>
                                                        )
                                                    }

                                                    return (
                                                        <>
                                                            <Typography
                                                                variant="body2"
                                                                color={field.selected_value ? "primary" : "text.primary"}
                                                                fontWeight={field.selected_value ? "medium" : "normal"}
                                                            >
                                                                {field.selected_value || "—"}
                                                            </Typography>
                                                            <Typography variant="caption" color="text.secondary">
                                                                ({valueCount})
                                                            </Typography>
                                                        </>
                                                    )
                                                    })()}
                                                </Box>
                                                <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 1 }}>
                                                    <Typography variant="caption" color="text.secondary">
                                                        Row scope
                                                    </Typography>
                                                    <FormControl size="small" sx={{ minWidth: 170 }}>
                                                        <Select
                                                            value={getRowScopeValue(field)}
                                                            disabled={!!savingRowScopeById[field.id]}
                                                            onClick={(e) => e.stopPropagation()}
                                                            onMouseDown={(e) => e.stopPropagation()}
                                                            onChange={(e) => {
                                                                e.stopPropagation()
                                                                handleInlineRowScopeChange(field.id, e.target.value as EbayRowScope)
                                                            }}
                                                            displayEmpty
                                                        >
                                                            <MenuItem value="both">Both</MenuItem>
                                                            <MenuItem value="parent_only">Parent only</MenuItem>
                                                            <MenuItem value="variation_only">Variations only</MenuItem>
                                                        </Select>
                                                    </FormControl>
                                                </Box>
                                            </Box>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Paper>
            ) : (
                <Paper sx={{ p: 5, textAlign: 'center', mt: 4 }} variant="outlined">
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                        No fields found.
                    </Typography>
                    <Typography color="text.secondary">
                        Upload a template and click "Parse" to begin.
                    </Typography>
                </Paper>
            )}

            {/* Field Details Modal */}
            <FieldDetailsModal
                open={modalOpen}
                field={selectedField}
                onClose={() => setModalOpen(false)}
                onFieldUpdated={(updatedField) => {
                    // Update the field in parsedFields array
                    setParsedFields(prev => prev.map(f =>
                        f.id === updatedField.id ? updatedField : f
                    ))
                    // Also update selectedField so modal shows latest data
                    setSelectedField(updatedField)
                }}
            />

            {/* Preview Export Modal */}
            <Dialog open={previewOpen} onClose={() => setPreviewOpen(false)} maxWidth="lg" fullWidth>
                <DialogTitle>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="h6">eBay Template Preview</Typography>
                        <IconButton size="small" onClick={() => setPreviewOpen(false)}>
                            <CloseIcon />
                        </IconButton>
                    </Box>
                    {previewData && (
                        <Box>
                            <Typography variant="body2" color="text.secondary">
                                {previewData.original_filename} - Sheet: {previewData.sheet_name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Showing {previewData.preview_row_count} of {previewData.max_row} rows,
                                {previewData.preview_column_count} of {previewData.max_column} columns
                            </Typography>
                        </Box>
                    )}
                </DialogTitle>
                <DialogContent dividers>
                    {previewLoading && (
                        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                            <Typography>Loading preview...</Typography>
                        </Box>
                    )}
                    {previewError && (
                        <Alert severity="error" onClose={() => setPreviewError(null)}>
                            {previewError}
                        </Alert>
                    )}

                    {/* File Integrity Section */}
                    {integrityData && (
                        <Paper sx={{ p: 2, mb: 2, border: 1, borderColor: 'divider' }} variant="outlined">
                            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                File Integrity
                            </Typography>
                            <Stack spacing={1}>
                                <Box>
                                    <Typography variant="caption" color="text.secondary">Filename:</Typography>
                                    <Typography variant="body2">{integrityData.original_filename}</Typography>
                                </Box>
                                <Box>
                                    <Typography variant="caption" color="text.secondary">Size:</Typography>
                                    <Typography variant="body2">
                                        {integrityData.file_size.toLocaleString()} bytes ({(integrityData.file_size / 1024).toFixed(2)} KB)
                                    </Typography>
                                </Box>
                                {integrityData.sha256 && (
                                    <Box>
                                        <Typography variant="caption" color="text.secondary">SHA256:</Typography>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <Typography
                                                variant="body2"
                                                sx={{
                                                    fontFamily: 'monospace',
                                                    fontSize: '0.75rem',
                                                    wordBreak: 'break-all'
                                                }}
                                            >
                                                {integrityData.sha256.substring(0, 16)}...{integrityData.sha256.substring(integrityData.sha256.length - 16)}
                                            </Typography>
                                            <IconButton
                                                size="small"
                                                onClick={() => {
                                                    navigator.clipboard.writeText(integrityData.sha256!)
                                                    setSnackbarMessage('SHA256 copied to clipboard')
                                                }}
                                                title="Copy full hash"
                                            >
                                                <ContentCopyIcon fontSize="small" />
                                            </IconButton>
                                        </Box>
                                    </Box>
                                )}
                                {integrityData.uploaded_at && (
                                    <Box>
                                        <Typography variant="caption" color="text.secondary">Uploaded:</Typography>
                                        <Typography variant="body2">
                                            {new Date(integrityData.uploaded_at).toLocaleString()}
                                        </Typography>
                                    </Box>
                                )}
                            </Stack>
                        </Paper>
                    )}
                    {integrityLoading && !integrityData && (
                        <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
                            Loading integrity information...
                        </Typography>
                    )}
                    {!integrityData && !integrityLoading && previewData && (
                        <Alert severity="warning" sx={{ mb: 2 }}>
                            Integrity info unavailable.
                        </Alert>
                    )}

                    {/* File Verification Section */}
                    <Paper sx={{ p: 2, mb: 2, border: 1, borderColor: 'divider' }} variant="outlined">
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                            <Typography variant="subtitle2" fontWeight="bold">
                                🔍 File Verification
                            </Typography>
                            <Button
                                size="small"
                                variant="outlined"
                                onClick={handleVerifyNow}
                                disabled={verificationLoading}
                            >
                                {verificationLoading ? 'Verifying...' : 'Verify Now'}
                            </Button>
                        </Box>

                        {verificationData && (
                            <Stack spacing={1}>
                                {/* Status Badge */}
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    {verificationData.status === 'match' && (
                                        <>
                                            <CheckCircleOutlineIcon color="success" />
                                            <Typography variant="body2" color="success.main">
                                                Verified — file matches disk
                                            </Typography>
                                        </>
                                    )}
                                    {verificationData.status === 'mismatch' && (
                                        <>
                                            <WarningAmberIcon color="error" />
                                            <Typography variant="body2" color="error.main">
                                                Mismatch detected
                                            </Typography>
                                        </>
                                    )}
                                    {verificationData.status === 'missing' && (
                                        <>
                                            <WarningAmberIcon color="warning" />
                                            <Typography variant="body2" color="warning.main">
                                                File missing on disk
                                            </Typography>
                                        </>
                                    )}
                                    {verificationData.status === 'unknown' && (
                                        <>
                                            <InfoOutlinedIcon color="info" />
                                            <Typography variant="body2" color="text.secondary">
                                                No stored hash to verify against
                                            </Typography>
                                        </>
                                    )}
                                </Box>

                                {/* Comparison Details */}
                                {(verificationData.stored_sha256 || verificationData.computed_sha256) && (
                                    <Box>
                                        <Typography variant="caption" color="text.secondary">SHA256 Comparison:</Typography>
                                        <Stack direction="row" spacing={2} sx={{ mt: 0.5 }}>
                                            <Box sx={{ flex: 1 }}>
                                                <Typography variant="caption" color="text.secondary">Stored:</Typography>
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                                                        {verificationData.stored_sha256 ?
                                                            `${verificationData.stored_sha256.substring(0, 12)}...${verificationData.stored_sha256.substring(verificationData.stored_sha256.length - 12)}`
                                                            : 'N/A'}
                                                    </Typography>
                                                    {verificationData.stored_sha256 && (
                                                        <IconButton
                                                            size="small"
                                                            onClick={() => {
                                                                navigator.clipboard.writeText(verificationData.stored_sha256!)
                                                                setSnackbarMessage('Stored SHA256 copied')
                                                            }}
                                                        >
                                                            <ContentCopyIcon fontSize="small" />
                                                        </IconButton>
                                                    )}
                                                </Box>
                                            </Box>
                                            <Box sx={{ flex: 1 }}>
                                                <Typography variant="caption" color="text.secondary">Computed:</Typography>
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                                                        {verificationData.computed_sha256 ?
                                                            `${verificationData.computed_sha256.substring(0, 12)}...${verificationData.computed_sha256.substring(verificationData.computed_sha256.length - 12)}`
                                                            : 'N/A'}
                                                    </Typography>
                                                    {verificationData.computed_sha256 && (
                                                        <IconButton
                                                            size="small"
                                                            onClick={() => {
                                                                navigator.clipboard.writeText(verificationData.computed_sha256!)
                                                                setSnackbarMessage('Computed SHA256 copied')
                                                            }}
                                                        >
                                                            <ContentCopyIcon fontSize="small" />
                                                        </IconButton>
                                                    )}
                                                </Box>
                                            </Box>
                                        </Stack>
                                    </Box>
                                )}

                                {/* File Size Comparison */}
                                {(verificationData.stored_file_size !== undefined || verificationData.computed_file_size !== undefined) && (
                                    <Box>
                                        <Typography variant="caption" color="text.secondary">File Size:</Typography>
                                        <Typography variant="body2">
                                            Stored: {verificationData.stored_file_size !== undefined ? `${verificationData.stored_file_size.toLocaleString()} bytes` : 'N/A'} |
                                            Computed: {verificationData.computed_file_size !== undefined ? `${verificationData.computed_file_size.toLocaleString()} bytes` : 'N/A'}
                                        </Typography>
                                    </Box>
                                )}

                                {/* Verification Timestamp */}
                                <Box>
                                    <Typography variant="caption" color="text.secondary">Verified at:</Typography>
                                    <Typography variant="body2">
                                        {new Date(verificationData.verified_at).toLocaleString()}
                                    </Typography>
                                </Box>
                            </Stack>
                        )}

                        {!verificationData && !verificationLoading && (
                            <Typography variant="body2" color="text.secondary">
                                Click "Verify Now" to check if the file on disk matches stored integrity data.
                            </Typography>
                        )}
                    </Paper>

                    {previewData && !previewLoading && (
                        <Box sx={{ overflowX: 'auto' }}>
                            <Table size="small" sx={{ minWidth: 650 }}>
                                <TableHead>
                                    <TableRow>
                                        {previewData.grid[0]?.map((_, colIdx) => (
                                            <TableCell key={colIdx} sx={{ fontWeight: 'bold', backgroundColor: 'action.hover' }}>
                                                Col {colIdx + 1}
                                            </TableCell>
                                        ))}
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {previewData.grid.map((row, rowIdx) => (
                                        <TableRow key={rowIdx} hover>
                                            {row.map((cell, cellIdx) => (
                                                <TableCell key={cellIdx} sx={{ whiteSpace: 'nowrap', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                    {cell || <Typography variant="caption" color="text.disabled">(empty)</Typography>}
                                                </TableCell>
                                            ))}
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </Box>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button
                        variant="contained"
                        startIcon={<DownloadIcon />}
                        onClick={() => window.open(ebayTemplatesApi.downloadCurrentTemplateUrl(), '_blank')}
                        disabled={!previewData}
                    >
                        Download XLSX
                    </Button>
                    <Button onClick={() => setPreviewOpen(false)}>Close</Button>
                </DialogActions>
            </Dialog>

            {/* Snackbar for notifications */}
            <Snackbar
                open={Boolean(snackbarMessage)}
                autoHideDuration={6000}
                onClose={() => setSnackbarMessage(null)}
                message={snackbarMessage}
            />
        </Box>
    )
}
