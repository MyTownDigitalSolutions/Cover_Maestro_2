import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Container,
  FormControl,
  FormHelperText,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Stack,
  Switch,
  Chip,
  TextField,
  Typography,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ChevronRightIcon from '@mui/icons-material/ChevronRight'
import type { SelectChangeEvent } from '@mui/material/Select'
import {
  ebayStoreCategoryNodesApi,
  equipmentTypesApi,
  manufacturersApi,
  seriesApi,
  modelsApi,
  type EbayStoreCategoryNode,
  type EbayStoreCategoryNodeBindingCreate,
  type EbayStoreCategoryNodeBindingType,
  type EbayStoreCategoryNodeLevel,
} from '../services/api'
import type { EquipmentType, Manufacturer, Series, Model } from '../types'

type NodeEditState = {
  name: string
  storeCategoryNumberInput: string
  bindingType: EbayStoreCategoryNodeBindingType
  selectedBindingIds: number[]
  bindingLabel: string
}

type BindingOption = { id: number; label: string }

const LEVEL_OPTIONS: Array<{ value: EbayStoreCategoryNodeLevel; label: string }> = [
  { value: 'top', label: 'Top' },
  { value: 'second', label: 'Second' },
  { value: 'third', label: 'Third' },
]

const BINDING_OPTIONS: Array<{ value: EbayStoreCategoryNodeBindingType; label: string }> = [
  { value: 'none', label: 'None' },
  { value: 'equipment_type', label: 'Equipment Type' },
  { value: 'manufacturer', label: 'Manufacturer' },
  { value: 'series', label: 'Series' },
  { value: 'model', label: 'Model' },
  { value: 'custom', label: 'Custom' },
]

const ALLOWED_BINDINGS_BY_LEVEL: Record<EbayStoreCategoryNodeLevel, EbayStoreCategoryNodeBindingType[]> = {
  top: ['none', 'equipment_type'],
  second: ['none', 'manufacturer', 'equipment_type'],
  third: ['none', 'manufacturer', 'series', 'model'],
}

const BINDING_HELPER_BY_LEVEL: Record<EbayStoreCategoryNodeLevel, string> = {
  top: 'Top level nodes typically bind to Equipment Types.',
  second: 'Second level nodes typically bind to Equipment Types or Manufacturers.',
  third: 'Third level nodes typically bind to Manufacturers, Series, or Models.',
}

export default function EbayStoreCategoryHierarchyPage() {
  const [loading, setLoading] = useState(false)
  const [nodes, setNodes] = useState<EbayStoreCategoryNode[]>([])
  const [equipmentTypes, setEquipmentTypes] = useState<EquipmentType[]>([])
  const [manufacturers, setManufacturers] = useState<Manufacturer[]>([])
  const [seriesList, setSeriesList] = useState<Series[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [error, setError] = useState<string | null>(null)
  const [snackbarMessage, setSnackbarMessage] = useState<string | null>(null)

  const [createLevel, setCreateLevel] = useState<EbayStoreCategoryNodeLevel>('top')
  const [createParentId, setCreateParentId] = useState<number | ''>('')
  const [createName, setCreateName] = useState('')
  const [createStoreCategoryNumberInput, setCreateStoreCategoryNumberInput] = useState('')
  const [createBindingType, setCreateBindingType] = useState<EbayStoreCategoryNodeBindingType>('none')
  const [createSelectedBindingIds, setCreateSelectedBindingIds] = useState<number[]>([])
  const [createBindingLabel, setCreateBindingLabel] = useState('')
  const [creating, setCreating] = useState(false)

  const [savingIds, setSavingIds] = useState<Record<number, boolean>>({})
  const [enabledSavingIds, setEnabledSavingIds] = useState<Record<number, boolean>>({})
  const [deletingIds, setDeletingIds] = useState<Record<number, boolean>>({})
  const [editsById, setEditsById] = useState<Record<number, NodeEditState>>({})
  const [expandedTopIds, setExpandedTopIds] = useState<Record<number, boolean>>({})
  const [expandedSecondIds, setExpandedSecondIds] = useState<Record<number, boolean>>({})
  const [inlineParentId, setInlineParentId] = useState<number | null>(null)
  const [inlineLevel, setInlineLevel] = useState<EbayStoreCategoryNodeLevel | null>(null)
  const [inlineName, setInlineName] = useState('')
  const [inlineStoreCategoryNumberInput, setInlineStoreCategoryNumberInput] = useState('')
  const [inlineBindingType, setInlineBindingType] = useState<EbayStoreCategoryNodeBindingType>('none')
  const [inlineSelectedBindingIds, setInlineSelectedBindingIds] = useState<number[]>([])
  const [inlineBindingLabel, setInlineBindingLabel] = useState('')
  const [inlineCreating, setInlineCreating] = useState(false)

  const sortHierarchyNodes = (a: EbayStoreCategoryNode, b: EbayStoreCategoryNode) => {
    const byName = (a.name || '').localeCompare((b.name || ''), undefined, { sensitivity: 'base', numeric: true })
    if (byName !== 0) return byName
    return a.id - b.id
  }

  const topNodes = useMemo(
    () => [...nodes.filter((n) => n.level === 'top')].sort(sortHierarchyNodes),
    [nodes]
  )
  const secondNodes = useMemo(
    () => [...nodes.filter((n) => n.level === 'second')].sort(sortHierarchyNodes),
    [nodes]
  )

  const parentOptionsForCreate = useMemo(() => {
    if (createLevel === 'second') return topNodes
    if (createLevel === 'third') return secondNodes
    return []
  }, [createLevel, topNodes, secondNodes])

  const thirdBySecondParent = useMemo(() => {
    const out: Record<number, EbayStoreCategoryNode[]> = {}
    for (const node of nodes) {
      if (node.level !== 'third' || node.parent_id == null) continue
      if (!out[node.parent_id]) out[node.parent_id] = []
      out[node.parent_id].push(node)
    }
    for (const key of Object.keys(out)) {
      out[Number(key)].sort(sortHierarchyNodes)
    }
    return out
  }, [nodes])

  const secondByTopParent = useMemo(() => {
    const out: Record<number, EbayStoreCategoryNode[]> = {}
    for (const node of nodes) {
      if (node.level !== 'second' || node.parent_id == null) continue
      if (!out[node.parent_id]) out[node.parent_id] = []
      out[node.parent_id].push(node)
    }
    for (const key of Object.keys(out)) {
      out[Number(key)].sort(sortHierarchyNodes)
    }
    return out
  }, [nodes])

  const bindingOptionsByType = useMemo(() => {
    return {
      equipment_type: equipmentTypes.map((it) => ({ id: it.id, label: it.name })).sort(sortBindingOptions),
      manufacturer: manufacturers.map((it) => ({ id: it.id, label: it.name })).sort(sortBindingOptions),
      series: seriesList.map((it) => ({ id: it.id, label: it.name })).sort(sortBindingOptions),
      model: models.map((it) => ({ id: it.id, label: it.name })).sort(sortBindingOptions),
    } as const
  }, [equipmentTypes, manufacturers, seriesList, models])

  const getBindingOptions = (bindingType: EbayStoreCategoryNodeBindingType) => {
    if (bindingType === 'equipment_type' || bindingType === 'manufacturer' || bindingType === 'series' || bindingType === 'model') {
      return bindingOptionsByType[bindingType]
    }
    return []
  }

  const getParentBindingContext = (parentNode: EbayStoreCategoryNode | null) => {
    if (!parentNode) return null
    const parentBindingType = parentNode.binding_type
    const parentBindingIds = (parentNode.bindings || []).map((b) => b.binding_id)
    if (parentBindingType === 'none' || parentBindingType === 'custom' || parentBindingIds.length === 0) {
      return null
    }
    return { parentBindingType, parentBindingIds }
  }

  const getFilteredBindingOptions = (
    bindingType: EbayStoreCategoryNodeBindingType,
    parentNode: EbayStoreCategoryNode | null
  ) => {
    const baseOptions = getBindingOptions(bindingType)
    const parentContext = getParentBindingContext(parentNode)
    if (!parentContext) return baseOptions

    if (parentContext.parentBindingType === 'manufacturer' && bindingType === 'series') {
      const allowedManufacturerIds = new Set(parentContext.parentBindingIds)
      return baseOptions.filter((opt) => {
        const series = seriesList.find((s) => s.id === opt.id)
        return series != null && allowedManufacturerIds.has(series.manufacturer_id)
      }).sort(sortBindingOptions)
    }

    if (parentContext.parentBindingType === 'series' && bindingType === 'model') {
      const allowedSeriesIds = new Set(parentContext.parentBindingIds)
      return baseOptions.filter((opt) => {
        const model = models.find((m) => m.id === opt.id)
        return model != null && allowedSeriesIds.has(model.series_id)
      }).sort(sortBindingOptions)
    }

    return baseOptions
  }

  const getCascadingEmptyHelperText = (
    bindingType: EbayStoreCategoryNodeBindingType,
    parentNode: EbayStoreCategoryNode | null,
    filteredCount: number
  ) => {
    if (filteredCount > 0) return ''
    const parentContext = getParentBindingContext(parentNode)
    if (!parentContext) return ''
    if (parentContext.parentBindingType === 'manufacturer' && bindingType === 'series') {
      return 'No series available for the selected parent manufacturer binding.'
    }
    if (parentContext.parentBindingType === 'series' && bindingType === 'model') {
      return 'No models available for the selected parent series binding.'
    }
    return ''
  }

  const createParentNode = useMemo(() => {
    if (createParentId === '') return null
    return nodes.find((n) => n.id === createParentId) || null
  }, [createParentId, nodes])

  const createFilteredBindingOptions = useMemo(
    () => getFilteredBindingOptions(createBindingType, createParentNode),
    [createBindingType, createParentNode, bindingOptionsByType, seriesList, models]
  )
  const inlineParentNode = useMemo(() => {
    if (inlineParentId == null) return null
    return nodes.find((n) => n.id === inlineParentId) || null
  }, [inlineParentId, nodes])
  const inlineFilteredBindingOptions = useMemo(
    () => getFilteredBindingOptions(inlineBindingType, inlineParentNode),
    [inlineBindingType, inlineParentNode, bindingOptionsByType, seriesList, models]
  )

  const getBindingLabelForId = (bindingType: EbayStoreCategoryNodeBindingType, bindingId: number) => {
    const opt = getBindingOptions(bindingType).find((o) => o.id === bindingId)
    return opt ? opt.label : String(bindingId)
  }

  const isBindingTypeAllowedForLevel = (level: EbayStoreCategoryNodeLevel, bindingType: EbayStoreCategoryNodeBindingType) => {
    return ALLOWED_BINDINGS_BY_LEVEL[level].includes(bindingType)
  }

  const getBindingSummary = (node: EbayStoreCategoryNode) => {
    if ((node.bindings || []).length > 0) {
      const bindingType = node.bindings[0]?.binding_type
      const count = node.bindings.length
      if (bindingType === 'equipment_type') return `Bound to ${count} Equipment Type${count === 1 ? '' : 's'}`
      if (bindingType === 'manufacturer') return `Bound to ${count} Manufacturer${count === 1 ? '' : 's'}`
      if (bindingType === 'series') return `Bound to ${count} Series`
      if (bindingType === 'model') return `Bound to ${count} Model${count === 1 ? '' : 's'}`
      return `Bound to ${count} item${count === 1 ? '' : 's'}`
    }
    return 'No binding (global)'
  }

  const loadNodes = async () => {
    setLoading(true)
    setError(null)
    try {
      const [rows, ets, mfrs, allSeries, allModels] = await Promise.all([
        ebayStoreCategoryNodesApi.list({ system: 'ebay', include_disabled: true }),
        equipmentTypesApi.list(),
        manufacturersApi.list(),
        seriesApi.list(),
        modelsApi.list(),
      ])
      setNodes(rows)
      setEquipmentTypes(ets)
      setManufacturers(mfrs)
      setSeriesList(allSeries)
      setModels(allModels)
      setEditsById(
        Object.fromEntries(
          rows.map((row) => [
            row.id,
            {
              name: row.name,
              storeCategoryNumberInput: String(row.store_category_number ?? ''),
              bindingType: row.binding_type,
              selectedBindingIds: (row.bindings || []).map((b) => b.binding_id),
              bindingLabel: row.binding_label ?? '',
            },
          ])
        )
      )
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load eBay store category hierarchy')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadNodes()
  }, [])

  useEffect(() => {
    if (createBindingType === 'none' || createBindingType === 'custom') return
    const allowedIds = new Set(createFilteredBindingOptions.map((opt) => opt.id))
    setCreateSelectedBindingIds((prev) => prev.filter((id) => allowedIds.has(id)))
  }, [createBindingType, createParentId, createFilteredBindingOptions])

  useEffect(() => {
    if (inlineBindingType === 'none' || inlineBindingType === 'custom') return
    const allowedIds = new Set(inlineFilteredBindingOptions.map((opt) => opt.id))
    setInlineSelectedBindingIds((prev) => prev.filter((id) => allowedIds.has(id)))
  }, [inlineBindingType, inlineParentId, inlineFilteredBindingOptions])

  useEffect(() => {
    setEditsById((prev) => {
      let changed = false
      const next: Record<number, NodeEditState> = {}
      for (const [idRaw, edits] of Object.entries(prev)) {
        const nodeId = Number(idRaw)
        const node = nodes.find((n) => n.id === nodeId)
        if (!node || edits.bindingType === 'none' || edits.bindingType === 'custom') {
          next[nodeId] = edits
          continue
        }
        const parentNode = node.parent_id == null ? null : (nodes.find((n) => n.id === node.parent_id) || null)
        const allowedIds = new Set(getFilteredBindingOptions(edits.bindingType, parentNode).map((opt) => opt.id))
        const pruned = edits.selectedBindingIds.filter((bindingId) => allowedIds.has(bindingId))
        if (pruned.length !== edits.selectedBindingIds.length) {
          changed = true
          next[nodeId] = { ...edits, selectedBindingIds: pruned }
        } else {
          next[nodeId] = edits
        }
      }
      return changed ? next : prev
    })
  }, [nodes, seriesList, models, bindingOptionsByType])

  const parseRequiredInt = (raw: string, label: string): number => {
    const trimmed = raw.trim()
    if (!trimmed) throw new Error(`${label} is required`)
    const parsed = Number(trimmed)
    if (!Number.isInteger(parsed)) throw new Error(`${label} must be an integer`)
    return parsed
  }

  const handleCreate = async () => {
    if (!createName.trim()) {
      setError('Name is required')
      return
    }
    if ((createLevel === 'second' || createLevel === 'third') && createParentId === '') {
      setError('Parent is required for this level')
      return
    }

    let storeCategoryNumber: number
    let bindings: EbayStoreCategoryNodeBindingCreate[] = []
    let bindingLabel: string | null = null
    const createAllowedIds = new Set(createFilteredBindingOptions.map((opt) => opt.id))
    const effectiveCreateSelectedBindingIds =
      createBindingType === 'none' || createBindingType === 'custom'
        ? []
        : createSelectedBindingIds.filter((id) => createAllowedIds.has(id))

    try {
      storeCategoryNumber = parseRequiredInt(createStoreCategoryNumberInput, 'Store Category Number')
      if (createBindingType === 'custom') {
        bindingLabel = createBindingLabel.trim()
        if (!bindingLabel) {
          setError('Binding Label is required for custom binding')
          return
        }
      } else if (createBindingType !== 'none') {
        if (effectiveCreateSelectedBindingIds.length === 0) {
          setError('Select at least one binding')
          return
        }
        bindings = effectiveCreateSelectedBindingIds.map((id) => ({
          binding_type: createBindingType,
          binding_id: id,
        }))
      }
    } catch (e: any) {
      setError(e.message)
      return
    }

    setCreating(true)
    setError(null)
    try {
      await ebayStoreCategoryNodesApi.create({
        system: 'ebay',
        level: createLevel,
        parent_id: createLevel === 'top' ? null : (createParentId as number),
        name: createName.trim(),
        store_category_number: storeCategoryNumber,
        binding_type: createBindingType,
        bindings,
        binding_label: bindingLabel,
        is_enabled: true,
      })
      setCreateName('')
      setCreateStoreCategoryNumberInput('')
      setCreateBindingType('none')
      setCreateSelectedBindingIds([])
      setCreateBindingLabel('')
      setSnackbarMessage('Node created')
      await loadNodes()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create node')
    } finally {
      setCreating(false)
    }
  }

  const handleToggleEnabled = async (node: EbayStoreCategoryNode, checked: boolean) => {
    setEnabledSavingIds((prev) => ({ ...prev, [node.id]: true }))
    setError(null)
    try {
      const updated = await ebayStoreCategoryNodesApi.update(node.id, { is_enabled: checked })
      setNodes((prev) => prev.map((n) => (n.id === node.id ? updated : n)))
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update enabled state')
    } finally {
      setEnabledSavingIds((prev) => ({ ...prev, [node.id]: false }))
    }
  }

  const handleSaveNode = async (node: EbayStoreCategoryNode) => {
    const edits = editsById[node.id]
    if (!edits) return
    const parentNode = node.parent_id == null ? null : (nodes.find((n) => n.id === node.parent_id) || null)
    const filteredOptions = getFilteredBindingOptions(edits.bindingType, parentNode)
    const allowedIds = new Set(filteredOptions.map((opt) => opt.id))
    const effectiveSelectedBindingIds =
      edits.bindingType === 'none' || edits.bindingType === 'custom'
        ? []
        : edits.selectedBindingIds.filter((id) => allowedIds.has(id))

    let storeCategoryNumber: number
    let bindings: EbayStoreCategoryNodeBindingCreate[] = []
    let bindingLabel: string | null = null
    try {
      storeCategoryNumber = parseRequiredInt(edits.storeCategoryNumberInput, 'Store Category Number')
      if (!edits.name.trim()) {
        setError('Name is required')
        return
      }
      if (edits.bindingType === 'custom') {
        bindingLabel = edits.bindingLabel.trim()
        if (!bindingLabel) {
          setError('Binding Label is required for custom binding')
          return
        }
      } else if (edits.bindingType !== 'none') {
        if (effectiveSelectedBindingIds.length === 0) {
          setError('Select at least one binding')
          return
        }
        bindings = effectiveSelectedBindingIds.map((id) => ({
          binding_type: edits.bindingType,
          binding_id: id,
        }))
      } else {
        bindingLabel = null
      }
    } catch (e: any) {
      setError(e.message)
      return
    }

    setSavingIds((prev) => ({ ...prev, [node.id]: true }))
    setError(null)
    try {
      const updated = await ebayStoreCategoryNodesApi.update(node.id, {
        name: edits.name.trim(),
        store_category_number: storeCategoryNumber,
        binding_type: edits.bindingType,
        bindings,
        binding_label: bindingLabel,
      })
      setNodes((prev) => prev.map((n) => (n.id === node.id ? updated : n)))
      setEditsById((prev) => ({
        ...prev,
        [node.id]: {
          ...prev[node.id],
          selectedBindingIds: (updated.bindings || []).map((b) => b.binding_id),
        },
      }))
      setSnackbarMessage('Node updated')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update node')
    } finally {
      setSavingIds((prev) => ({ ...prev, [node.id]: false }))
    }
  }

  const handleDeleteNode = async (node: EbayStoreCategoryNode) => {
    if (!window.confirm(`Delete node "${node.name}"?`)) return
    setDeletingIds((prev) => ({ ...prev, [node.id]: true }))
    setError(null)
    try {
      await ebayStoreCategoryNodesApi.remove(node.id)
      setNodes((prev) => prev.filter((n) => n.id !== node.id))
      setSnackbarMessage('Node deleted')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete node')
    } finally {
      setDeletingIds((prev) => ({ ...prev, [node.id]: false }))
    }
  }

  const resetInlineCreateState = () => {
    setInlineName('')
    setInlineStoreCategoryNumberInput('')
    setInlineBindingType('none')
    setInlineSelectedBindingIds([])
    setInlineBindingLabel('')
  }

  const handleAddSubLevel = (node: EbayStoreCategoryNode) => {
    if (node.level === 'third') return
    const nextLevel: EbayStoreCategoryNodeLevel = node.level === 'top' ? 'second' : 'third'
    if (inlineParentId === node.id && inlineLevel === nextLevel) {
      setInlineParentId(null)
      setInlineLevel(null)
      resetInlineCreateState()
      return
    }
    if (node.level === 'top') {
      setExpandedTopIds((prev) => ({ ...prev, [node.id]: true }))
    } else if (node.level === 'second') {
      setExpandedSecondIds((prev) => ({ ...prev, [node.id]: true }))
      if (node.parent_id != null) {
        setExpandedTopIds((prev) => ({ ...prev, [node.parent_id!]: true }))
      }
    }
    setInlineParentId(node.id)
    setInlineLevel(nextLevel)
    resetInlineCreateState()
  }

  const handleInlineCreate = async () => {
    if (!inlineLevel || inlineParentId == null) return
    if (!inlineName.trim()) {
      setError('Name is required')
      return
    }
    let storeCategoryNumber: number
    let bindings: EbayStoreCategoryNodeBindingCreate[] = []
    let bindingLabel: string | null = null
    const inlineAllowedIds = new Set(inlineFilteredBindingOptions.map((opt) => opt.id))
    const effectiveInlineSelectedBindingIds =
      inlineBindingType === 'none' || inlineBindingType === 'custom'
        ? []
        : inlineSelectedBindingIds.filter((id) => inlineAllowedIds.has(id))
    try {
      storeCategoryNumber = parseRequiredInt(inlineStoreCategoryNumberInput, 'Store Category Number')
      if (inlineBindingType === 'custom') {
        bindingLabel = inlineBindingLabel.trim()
        if (!bindingLabel) {
          setError('Binding Label is required for custom binding')
          return
        }
      } else if (inlineBindingType !== 'none') {
        if (effectiveInlineSelectedBindingIds.length === 0) {
          setError('Select at least one binding')
          return
        }
        bindings = effectiveInlineSelectedBindingIds.map((id) => ({
          binding_type: inlineBindingType,
          binding_id: id,
        }))
      }
    } catch (e: any) {
      setError(e.message)
      return
    }
    setInlineCreating(true)
    setError(null)
    try {
      await ebayStoreCategoryNodesApi.create({
        system: 'ebay',
        level: inlineLevel,
        parent_id: inlineParentId,
        name: inlineName.trim(),
        store_category_number: storeCategoryNumber,
        binding_type: inlineBindingType,
        bindings,
        binding_label: bindingLabel,
        is_enabled: true,
      })
      setSnackbarMessage('Node created')
      setInlineParentId(null)
      setInlineLevel(null)
      resetInlineCreateState()
      await loadNodes()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create node')
    } finally {
      setInlineCreating(false)
    }
  }

  const renderInlineCreateForm = (depth: number) => {
    if (!inlineLevel || inlineParentId == null) return null
    return (
      <Paper
        variant="outlined"
        sx={{
          p: 1.5,
          mb: 1,
          ml: depth * 3 + 3,
          borderStyle: 'dashed',
        }}
      >
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }} useFlexGap flexWrap="wrap">
          <Typography variant="body2" sx={{ minWidth: 120 }}>
            Quick Add {inlineLevel === 'second' ? 'Second' : 'Third'} Level
          </Typography>
          <TextField
            size="small"
            label="Name"
            value={inlineName}
            onChange={(e) => setInlineName(e.target.value)}
            sx={{ minWidth: 180 }}
          />
          <TextField
            size="small"
            label="Store Category Number"
            type="number"
            value={inlineStoreCategoryNumberInput}
            onChange={(e) => setInlineStoreCategoryNumberInput(e.target.value)}
            sx={{ minWidth: 190 }}
          />
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel id="inline-binding-type-label">Binding Type</InputLabel>
            <Select
              labelId="inline-binding-type-label"
              value={inlineBindingType}
              label="Binding Type"
              onChange={(e) => {
                const next = e.target.value as EbayStoreCategoryNodeBindingType
                setInlineBindingType(next)
                if (next === 'none') {
                  setInlineSelectedBindingIds([])
                  setInlineBindingLabel('')
                }
                if (next === 'custom') {
                  setInlineSelectedBindingIds([])
                }
                if (next !== 'custom') {
                  setInlineBindingLabel('')
                }
                if (next !== 'none' && next !== 'custom') {
                  const allowedIds = new Set(getFilteredBindingOptions(next, inlineParentNode).map((opt) => opt.id))
                  setInlineSelectedBindingIds((prev) => prev.filter((id) => allowedIds.has(id)))
                }
              }}
            >
              {BINDING_OPTIONS.map((opt) => (
                <MenuItem
                  key={opt.value}
                  value={opt.value}
                  disabled={!isBindingTypeAllowedForLevel(inlineLevel, opt.value)}
                >
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>{BINDING_HELPER_BY_LEVEL[inlineLevel]}</FormHelperText>
          </FormControl>
          {inlineBindingType === 'custom' ? (
            <TextField
              size="small"
              label="Binding Label"
              value={inlineBindingLabel}
              onChange={(e) => setInlineBindingLabel(e.target.value)}
              sx={{ minWidth: 170 }}
            />
          ) : inlineBindingType !== 'none' ? (
            <Stack direction="row" spacing={1} alignItems="center" sx={{ minWidth: 320 }}>
              <FormControl size="small" sx={{ minWidth: 220 }}>
                <InputLabel id="inline-binding-ids-label">Bindings</InputLabel>
                <Select
                  multiple
                  labelId="inline-binding-ids-label"
                  value={inlineSelectedBindingIds.map(String)}
                  label="Bindings"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {(selected as string[]).map((sid) => (
                        <Chip key={sid} size="small" label={getBindingLabelForId(inlineBindingType, Number(sid))} />
                      ))}
                    </Box>
                  )}
                  onChange={(e) => setInlineSelectedBindingIds((e.target.value as string[]).map((v) => Number(v)))}
                >
                  {inlineFilteredBindingOptions.map((opt) => (
                    <MenuItem key={opt.id} value={String(opt.id)}>
                      {opt.label}
                    </MenuItem>
                  ))}
                </Select>
                {getCascadingEmptyHelperText(inlineBindingType, inlineParentNode, inlineFilteredBindingOptions.length) && (
                  <FormHelperText>
                    {getCascadingEmptyHelperText(inlineBindingType, inlineParentNode, inlineFilteredBindingOptions.length)}
                  </FormHelperText>
                )}
              </FormControl>
              <Button size="small" onClick={() => setInlineSelectedBindingIds(inlineFilteredBindingOptions.map((opt) => opt.id))}>
                Select All
              </Button>
              <Button size="small" onClick={() => setInlineSelectedBindingIds([])}>
                Clear All
              </Button>
            </Stack>
          ) : null}
          <Button variant="contained" size="small" disabled={inlineCreating} onClick={handleInlineCreate}>
            {inlineCreating ? 'Creating...' : 'Create'}
          </Button>
          <Button
            size="small"
            onClick={() => {
              setInlineParentId(null)
              setInlineLevel(null)
              resetInlineCreateState()
            }}
          >
            Cancel
          </Button>
        </Stack>
      </Paper>
    )
  }

  const renderNodeRow = (node: EbayStoreCategoryNode, depth: number) => {
    const edits = editsById[node.id]
    if (!edits) return null
    const secondChildrenCount = node.level === 'top' ? (secondByTopParent[node.id] || []).length : 0
    const thirdChildrenCount = node.level === 'second' ? (thirdBySecondParent[node.id] || []).length : 0
    const isTopExpandable = node.level === 'top' && secondChildrenCount > 0
    const isSecondExpandable = node.level === 'second' && thirdChildrenCount > 0
    const isExpandable = isTopExpandable || isSecondExpandable
    const isExpanded =
      node.level === 'top'
        ? !!expandedTopIds[node.id]
        : node.level === 'second'
          ? !!expandedSecondIds[node.id]
          : false
    const parentNode = node.parent_id == null ? null : (nodes.find((n) => n.id === node.parent_id) || null)
    const filteredBindingOptions = getFilteredBindingOptions(edits.bindingType, parentNode)
    const filteredBindingOptionIds = new Set(filteredBindingOptions.map((opt) => opt.id))
    const safeSelectedBindingIds = edits.selectedBindingIds.filter((id) => filteredBindingOptionIds.has(id))

    const levelStyles = {
      top: { borderColor: 'primary.main', borderWidth: 4 },
      second: { borderColor: 'divider', borderWidth: 3 },
      third: { borderColor: 'grey.400', borderWidth: 2 },
    } as const
    const levelStyle = levelStyles[node.level]

    return (
      <Paper
        key={node.id}
        variant="outlined"
        sx={{
          p: 1.5,
          mb: 1,
          ml: depth * 3,
          borderLeftStyle: 'solid',
          borderLeftColor: levelStyle.borderColor,
          borderLeftWidth: levelStyle.borderWidth,
        }}
      >
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }} useFlexGap flexWrap="wrap">
          {isExpandable && (
            <IconButton
              size="small"
              onClick={() => {
                if (node.level === 'top') {
                  setExpandedTopIds((prev) => ({ ...prev, [node.id]: !prev[node.id] }))
                } else if (node.level === 'second') {
                  setExpandedSecondIds((prev) => ({ ...prev, [node.id]: !prev[node.id] }))
                }
              }}
            >
              {isExpanded ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
            </IconButton>
          )}
          <Typography variant="body2" sx={{ minWidth: 90 }}>
            {node.level.toUpperCase()}
          </Typography>
          {node.level === 'top' && !isExpanded && secondChildrenCount > 0 && (
            <Typography variant="caption" color="text.secondary">
              {secondChildrenCount} second-level node{secondChildrenCount === 1 ? '' : 's'}
            </Typography>
          )}
          {node.level === 'second' && !isExpanded && thirdChildrenCount > 0 && (
            <Typography variant="caption" color="text.secondary">
              {thirdChildrenCount} third-level node{thirdChildrenCount === 1 ? '' : 's'}
            </Typography>
          )}
          <TextField
            size="small"
            label="Name"
            value={edits.name}
            onChange={(e) => setEditsById((prev) => ({ ...prev, [node.id]: { ...edits, name: e.target.value } }))}
            sx={{ minWidth: 180 }}
          />
          <TextField
            size="small"
            label="Store Category Number"
            type="number"
            value={edits.storeCategoryNumberInput}
            onChange={(e) => setEditsById((prev) => ({ ...prev, [node.id]: { ...edits, storeCategoryNumberInput: e.target.value } }))}
            sx={{ minWidth: 190 }}
          />
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel id={`binding-type-${node.id}`}>Binding Type</InputLabel>
            <Select
              labelId={`binding-type-${node.id}`}
              value={edits.bindingType}
              label="Binding Type"
              onChange={(e) => {
                const next = e.target.value as EbayStoreCategoryNodeBindingType
                const nextAllowedIds = new Set(getFilteredBindingOptions(next, parentNode).map((opt) => opt.id))
                setEditsById((prev) => ({
                  ...prev,
                  [node.id]: {
                    ...edits,
                    bindingType: next,
                    selectedBindingIds:
                      next === 'none' || next === 'custom'
                        ? []
                        : edits.selectedBindingIds.filter((id) => nextAllowedIds.has(id)),
                    bindingLabel: next === 'custom' ? edits.bindingLabel : '',
                  },
                }))
              }}
            >
              {BINDING_OPTIONS.map((opt) => (
                <MenuItem
                  key={opt.value}
                  value={opt.value}
                  disabled={!isBindingTypeAllowedForLevel(node.level, opt.value)}
                >
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>{BINDING_HELPER_BY_LEVEL[node.level]}</FormHelperText>
          </FormControl>
          {edits.bindingType === 'custom' ? (
            <TextField
              size="small"
              label="Binding Label"
              value={edits.bindingLabel}
              onChange={(e) => setEditsById((prev) => ({ ...prev, [node.id]: { ...edits, bindingLabel: e.target.value } }))}
              sx={{ minWidth: 170 }}
            />
          ) : edits.bindingType !== 'none' ? (
            <Stack direction="row" spacing={1} alignItems="center" sx={{ minWidth: 320 }}>
              <FormControl size="small" sx={{ minWidth: 220 }}>
                <InputLabel id={`binding-ids-${node.id}`}>Bindings</InputLabel>
                <Select
                  multiple
                  labelId={`binding-ids-${node.id}`}
                  value={safeSelectedBindingIds.map(String)}
                  label="Bindings"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {(selected as string[]).map((sid) => (
                        <Chip key={sid} size="small" label={getBindingLabelForId(edits.bindingType, Number(sid))} />
                      ))}
                    </Box>
                  )}
                  onChange={(e) => {
                    const selectedIds = (e.target.value as string[]).map((v) => Number(v))
                    setEditsById((prev) => ({
                      ...prev,
                      [node.id]: { ...edits, selectedBindingIds: selectedIds },
                    }))
                  }}
                >
                  {filteredBindingOptions.map((opt) => (
                    <MenuItem key={opt.id} value={String(opt.id)}>
                      {opt.label}
                    </MenuItem>
                  ))}
                </Select>
                {getCascadingEmptyHelperText(edits.bindingType, parentNode, filteredBindingOptions.length) && (
                  <FormHelperText>
                    {getCascadingEmptyHelperText(edits.bindingType, parentNode, filteredBindingOptions.length)}
                  </FormHelperText>
                )}
              </FormControl>
              <Button size="small" onClick={() => {
                const allIds = filteredBindingOptions.map((opt) => opt.id)
                setEditsById((prev) => ({ ...prev, [node.id]: { ...edits, selectedBindingIds: allIds } }))
              }}>
                Select All
              </Button>
              <Button size="small" onClick={() => {
                setEditsById((prev) => ({ ...prev, [node.id]: { ...edits, selectedBindingIds: [] } }))
              }}>
                Clear All
              </Button>
            </Stack>
          ) : null}
          <Stack direction="row" spacing={0.5} alignItems="center">
            <Typography variant="caption">Enabled</Typography>
            <Switch
              size="small"
              checked={node.is_enabled}
              disabled={!!enabledSavingIds[node.id]}
              onChange={(e) => handleToggleEnabled(node, e.target.checked)}
            />
          </Stack>
          <Typography variant="caption" color="text.secondary">
            {getBindingSummary(node)}
          </Typography>
          <Button
            variant="outlined"
            size="small"
            disabled={!!savingIds[node.id]}
            onClick={() => handleSaveNode(node)}
          >
            {savingIds[node.id] ? 'Saving...' : 'Save'}
          </Button>
          <Button
            color="error"
            size="small"
            disabled={!!deletingIds[node.id]}
            onClick={() => handleDeleteNode(node)}
          >
            {deletingIds[node.id] ? 'Deleting...' : 'Delete'}
          </Button>
          {node.level !== 'third' && (
            <Button
              size="small"
              onClick={() => handleAddSubLevel(node)}
            >
              {node.level === 'top' ? 'Add Second Level' : 'Add Third Level'}
            </Button>
          )}
        </Stack>
      </Paper>
    )
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        eBay Store Category Hierarchy
      </Typography>
      <Alert severity="info" sx={{ mb: 2 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
          How Store Category Matching Works
        </Typography>
        <Typography variant="body2">
          You build a 3-level hierarchy (Top -&gt; Second -&gt; Third). Nodes can bind to Equipment Types, Manufacturers,
          Series, or Models. During export, the deepest matching node is selected. If no match is found, fallback rules apply.
        </Typography>
      </Alert>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Create Node
        </Typography>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} useFlexGap flexWrap="wrap">
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel id="create-level-label">Level</InputLabel>
            <Select
              labelId="create-level-label"
              value={createLevel}
              label="Level"
              onChange={(e: SelectChangeEvent<EbayStoreCategoryNodeLevel>) => {
                const next = e.target.value as EbayStoreCategoryNodeLevel
                setCreateLevel(next)
                setCreateParentId('')
                if (!isBindingTypeAllowedForLevel(next, createBindingType)) {
                  setCreateBindingType('none')
                  setCreateSelectedBindingIds([])
                  setCreateBindingLabel('')
                }
              }}
            >
              {LEVEL_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 220 }} disabled={createLevel === 'top'}>
            <InputLabel id="create-parent-label">Parent</InputLabel>
            <Select
              labelId="create-parent-label"
              value={createParentId === '' ? '' : String(createParentId)}
              label="Parent"
              onChange={(e) => {
                const nextParentId = e.target.value === '' ? '' : Number(e.target.value)
                setCreateParentId(nextParentId)
                const nextParentNode = nextParentId === '' ? null : (nodes.find((n) => n.id === nextParentId) || null)
                const allowedIds = new Set(getFilteredBindingOptions(createBindingType, nextParentNode).map((opt) => opt.id))
                setCreateSelectedBindingIds((prev) => prev.filter((id) => allowedIds.has(id)))
              }}
            >
              {parentOptionsForCreate.map((node) => (
                <MenuItem key={node.id} value={String(node.id)}>
                  {node.name} ({node.store_category_number})
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            size="small"
            label="Name"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
            sx={{ minWidth: 200 }}
          />
          <TextField
            size="small"
            label="Store Category Number"
            type="number"
            value={createStoreCategoryNumberInput}
            onChange={(e) => setCreateStoreCategoryNumberInput(e.target.value)}
            sx={{ minWidth: 220 }}
          />

          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel id="create-binding-type-label">Binding Type</InputLabel>
            <Select
              labelId="create-binding-type-label"
              value={createBindingType}
              label="Binding Type"
              onChange={(e) => {
                const next = e.target.value as EbayStoreCategoryNodeBindingType
                setCreateBindingType(next)
                if (next === 'none') {
                  setCreateSelectedBindingIds([])
                  setCreateBindingLabel('')
                }
                if (next === 'custom') {
                  setCreateSelectedBindingIds([])
                }
                if (next !== 'custom') {
                  setCreateBindingLabel('')
                }
                if (next !== 'none' && next !== 'custom') {
                  const allowedIds = new Set(getFilteredBindingOptions(next, createParentNode).map((opt) => opt.id))
                  setCreateSelectedBindingIds((prev) => prev.filter((id) => allowedIds.has(id)))
                }
              }}
            >
              {BINDING_OPTIONS.map((opt) => (
                <MenuItem
                  key={opt.value}
                  value={opt.value}
                  disabled={!isBindingTypeAllowedForLevel(createLevel, opt.value)}
                >
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>{BINDING_HELPER_BY_LEVEL[createLevel]}</FormHelperText>
          </FormControl>

          {createBindingType === 'custom' ? (
            <TextField
              size="small"
              label="Binding Label"
              value={createBindingLabel}
              onChange={(e) => setCreateBindingLabel(e.target.value)}
              sx={{ minWidth: 200 }}
            />
          ) : createBindingType !== 'none' ? (
            <Stack direction="row" spacing={1} alignItems="center" sx={{ minWidth: 360 }}>
              <FormControl size="small" sx={{ minWidth: 240 }}>
                <InputLabel id="create-binding-ids-label">Bindings</InputLabel>
                <Select
                  multiple
                  labelId="create-binding-ids-label"
                  value={createSelectedBindingIds.map(String)}
                  label="Bindings"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {(selected as string[]).map((sid) => (
                        <Chip key={sid} size="small" label={getBindingLabelForId(createBindingType, Number(sid))} />
                      ))}
                    </Box>
                  )}
                  onChange={(e) => {
                    setCreateSelectedBindingIds((e.target.value as string[]).map((v) => Number(v)))
                  }}
                >
                  {createFilteredBindingOptions.map((opt) => (
                    <MenuItem key={opt.id} value={String(opt.id)}>
                      {opt.label}
                    </MenuItem>
                  ))}
                </Select>
                {getCascadingEmptyHelperText(createBindingType, createParentNode, createFilteredBindingOptions.length) && (
                  <FormHelperText>
                    {getCascadingEmptyHelperText(createBindingType, createParentNode, createFilteredBindingOptions.length)}
                  </FormHelperText>
                )}
              </FormControl>
              <Button size="small" onClick={() => setCreateSelectedBindingIds(createFilteredBindingOptions.map((opt) => opt.id))}>
                Select All
              </Button>
              <Button size="small" onClick={() => setCreateSelectedBindingIds([])}>
                Clear All
              </Button>
            </Stack>
          ) : null}

          <Button variant="contained" onClick={handleCreate} disabled={creating || loading}>
            {creating ? 'Creating...' : 'Create'}
          </Button>
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Browse / Edit
        </Typography>
        <Box>
          {topNodes.map((top) => (
            <Box key={top.id} sx={{ mb: 1.5 }}>
              {renderNodeRow(top, 0)}
              {inlineParentId === top.id && inlineLevel === 'second' && renderInlineCreateForm(1)}
              {!!expandedTopIds[top.id] && (secondByTopParent[top.id] || []).map((second) => (
                <Box key={second.id}>
                  {renderNodeRow(second, 1)}
                  {inlineParentId === second.id && inlineLevel === 'third' && renderInlineCreateForm(2)}
                  {!!expandedSecondIds[second.id] && (thirdBySecondParent[second.id] || []).map((third) => renderNodeRow(third, 2))}
                </Box>
              ))}
            </Box>
          ))}
          {!loading && topNodes.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No hierarchy nodes found.
            </Typography>
          )}
        </Box>
      </Paper>

      <Snackbar
        open={Boolean(snackbarMessage)}
        autoHideDuration={4000}
        onClose={() => setSnackbarMessage(null)}
        message={snackbarMessage}
      />
    </Container>
  )
}
  const sortBindingOptions = (a: BindingOption, b: BindingOption) => {
    const byLabel = a.label.localeCompare(b.label, undefined, { sensitivity: 'base', numeric: true })
    if (byLabel !== 0) return byLabel
    return a.id - b.id
  }
