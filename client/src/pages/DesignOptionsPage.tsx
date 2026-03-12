import { useEffect, useState } from 'react'
import {
  Box, Typography, Paper, Button, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, IconButton, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Select, MenuItem, FormControl, InputLabel, Chip, Switch, FormControlLabel,
  Snackbar, Alert
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import AddIcon from '@mui/icons-material/Add'
import { designOptionsApi, equipmentTypesApi } from '../services/api'
import type { DesignOption, EquipmentType } from '../types'

export default function DesignOptionsPage() {
  const [designOptions, setDesignOptions] = useState<DesignOption[]>([])
  const [equipmentTypes, setEquipmentTypes] = useState<EquipmentType[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<DesignOption | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [optionTypeSelect, setOptionTypeSelect] = useState('handle_location')
  const [customOptionType, setCustomOptionType] = useState('')
  const [isPricingRelevant, setIsPricingRelevant] = useState(false)
  const [equipmentTypeIds, setEquipmentTypeIds] = useState<number[]>([])
  const [skuAbbreviation, setSkuAbbreviation] = useState('')
  const [ebayVariationEnabled, setEbayVariationEnabled] = useState(false)

  const [price, setPrice] = useState<string>('0')
  const [placeholderToken, setPlaceholderToken] = useState('')
  const [saveError, setSaveError] = useState<string | null>(null)

  const normalizeNullableText = (value?: string | null) => {
    const trimmed = (value ?? '').trim()
    if (!trimmed || trimmed.toLowerCase() === 'none') return null
    return trimmed
  }

  const loadData = async () => {
    const [doData, etData] = await Promise.all([
      designOptionsApi.list(),
      equipmentTypesApi.list()
    ])
    setDesignOptions(doData)
    setEquipmentTypes(etData)
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleOpenDialog = (option?: DesignOption) => {
    if (option) {
      setEditing(option)
      setName(option.name)
      setDescription(option.description || '')

      const type = option.option_type || 'handle_location'
      if (['handle_location', 'angle_type', 'text_option', 'no_user_input_required'].includes(type)) {
        setOptionTypeSelect(type)
        setCustomOptionType('')
      } else {
        setOptionTypeSelect('__custom__')
        setCustomOptionType(type)
      }

      setEquipmentTypeIds(option.equipment_type_ids || [])
      setIsPricingRelevant(option.is_pricing_relevant || false)
      setSkuAbbreviation(option.sku_abbreviation || '')
      setEbayVariationEnabled(option.ebay_variation_enabled || false)
      setPrice(((option.price_cents || 0) / 100).toFixed(2))
      setPlaceholderToken(normalizeNullableText(option.placeholder_token) ?? '')
    } else {
      setEditing(null)
      setName('')
      setDescription('')
      setOptionTypeSelect('handle_location')
      setCustomOptionType('')
      setEquipmentTypeIds([])
      setIsPricingRelevant(false)
      setSkuAbbreviation('')
      setEbayVariationEnabled(false)
      setPrice('0')
      setPlaceholderToken('')
    }
    setDialogOpen(true)
  }

  const handleSave = async () => {
    let finalOptionType = optionTypeSelect
    if (finalOptionType === '__custom__') {
      finalOptionType = customOptionType.toLowerCase().trim()
        .replace(/[\s-]+/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_+|_+$/g, '')

      if (!finalOptionType) {
        alert('Custom option type is required')
        return
      }
    }

    const priceCents = Math.round(parseFloat(price) * 100)
    if (isNaN(priceCents) || priceCents < 0) {
      alert('Price must be a valid non-negative number')
      return
    }

    const data = {
      name: name.trim(),
      description: description || undefined,
      option_type: finalOptionType,
      is_pricing_relevant: isPricingRelevant,
      equipment_type_ids: Array.from(new Set(equipmentTypeIds.map(Number).filter(n => !Number.isNaN(n)))),
      sku_abbreviation: normalizeNullableText(skuAbbreviation),
      ebay_variation_enabled: ebayVariationEnabled,
      price_cents: priceCents,
      placeholder_token: normalizeNullableText(placeholderToken)
    }

    try {
      if (editing) {
        await designOptionsApi.update(editing.id, data)
      } else {
        await designOptionsApi.create(data)
      }
      setSaveError(null)
      setDialogOpen(false)
      await loadData()
    } catch (err: any) {
      console.error('Failed to save design option', err)
      const detail = err?.response?.data?.detail
      const message =
        typeof detail === 'string'
          ? detail
          : detail
            ? JSON.stringify(detail)
            : (err?.message || 'Unknown error')
      setSaveError(`Failed to save design option: ${message}`)
    }
  }

  const handleDelete = async (id: number) => {
    if (confirm('Are you sure you want to delete this product design option?')) {
      await designOptionsApi.delete(id)
      loadData()
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Product Design Options</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Add Product Design Option
        </Button>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="body2" color="text.secondary">
          Product design options are features that affect how models are configured (e.g., Handle Options, Angle Options).
          They can be assigned to equipment types to indicate which design features apply.
        </Typography>
      </Paper>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell align="right">Price</TableCell>
              <TableCell>Description</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {designOptions.map((option) => (
              <TableRow key={option.id}>
                <TableCell>{option.name}</TableCell>
                <TableCell><Chip label={option.option_type} size="small" /></TableCell>
                <TableCell align="right">${(option.price_cents / 100).toFixed(2)}</TableCell>
                <TableCell>{option.description || '-'}</TableCell>
                <TableCell align="right">
                  <IconButton onClick={() => handleOpenDialog(option)} size="small">
                    <EditIcon />
                  </IconButton>
                  <IconButton onClick={() => handleDelete(option.id)} size="small" color="error">
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {designOptions.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  No product design options found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? 'Edit Product Design Option' : 'Add Product Design Option'}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Name"
            fullWidth
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <FormControl fullWidth margin="dense">
            <InputLabel>Option Type</InputLabel>
            <Select
              value={optionTypeSelect}
              label="Option Type"
              onChange={(e) => setOptionTypeSelect(e.target.value)}
            >
              <MenuItem value="handle_location">Handle Location</MenuItem>
              <MenuItem value="angle_type">Angle Type</MenuItem>
              <MenuItem value="text_option">Text Option</MenuItem>
              <MenuItem value="no_user_input_required">No User Input Required</MenuItem>
              <MenuItem value="__custom__">Custom...</MenuItem>
            </Select>
          </FormControl>

          {optionTypeSelect === '__custom__' && (
            <TextField
              margin="dense"
              label="Custom Option Type"
              fullWidth
              value={customOptionType}
              onChange={(e) => setCustomOptionType(e.target.value)}
              helperText="Examples: pocket_style, vent_type"
            />
          )}

          <FormControl fullWidth margin="dense">
            <InputLabel>Assigned Equipment Types</InputLabel>
            <Select
              multiple
              value={equipmentTypeIds}
              label="Assigned Equipment Types"
              onChange={(e) => {
                const raw = e.target.value
                const arr = Array.isArray(raw) ? raw : String(raw).split(',')
                setEquipmentTypeIds(arr.map(Number).filter(n => !Number.isNaN(n)))
              }}
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((id) => {
                    const et = equipmentTypes.find(x => x.id === id)
                    return <Chip key={id} label={et ? et.name : id} size="small" />
                  })}
                </Box>
              )}
            >
              {equipmentTypes.map((et) => (
                <MenuItem key={et.id} value={et.id}>{et.name}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControlLabel
            control={<Switch checked={isPricingRelevant} onChange={(e) => setIsPricingRelevant(e.target.checked)} />}
            label="Used for pricing"
          />
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: -1, ml: 4, mb: 1 }}>
            If enabled, this option may later affect cost calculations.
          </Typography>

          <TextField
            margin="dense"
            label="Price (Add-on)"
            fullWidth
            type="number"
            inputProps={{ step: "0.01", min: "0" }}
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            InputProps={{
              startAdornment: <Typography sx={{ mr: 1 }}>$</Typography>
            }}
          />

          <TextField
            margin="dense"
            label="Placeholder Token"
            fullWidth
            value={placeholderToken}
            onChange={(e) => setPlaceholderToken(e.target.value)}
            placeholder="[SIDE_POCKET]"
            helperText="Used in Reverb template descriptions to inject the price"
          />

          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />

          <TextField
            margin="dense"
            label="SKU Abbreviation"
            fullWidth
            value={skuAbbreviation}
            onChange={(e) => setSkuAbbreviation(e.target.value)}
            inputProps={{ maxLength: 3 }}
            helperText="Max 3 characters for eBay variation SKUs"
          />

          <FormControlLabel
            control={<Switch checked={ebayVariationEnabled} onChange={(e) => setEbayVariationEnabled(e.target.checked)} />}
            label="eBay Variation Enabled"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={!name.trim()}>
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(saveError)}
        autoHideDuration={6000}
        onClose={() => setSaveError(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSaveError(null)} severity="error" variant="filled" sx={{ width: '100%' }}>
          {saveError}
        </Alert>
      </Snackbar>
    </Box>
  )
}
