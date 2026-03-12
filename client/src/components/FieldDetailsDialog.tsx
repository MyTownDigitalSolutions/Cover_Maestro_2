import { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  TextField,
  Chip,
  Divider,
  Alert,
  CircularProgress
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import CheckIcon from '@mui/icons-material/Check'
import type { ProductTypeField } from '../types'
import { templatesApi } from '../services/api'

interface FieldDetailsDialogProps {
  field: ProductTypeField
  onClose: () => void
  onUpdate: (updatedField: ProductTypeField) => void
}

export default function FieldDetailsDialog({ field, onClose, onUpdate }: FieldDetailsDialogProps) {
  const [validValues, setValidValues] = useState(field.valid_values)
  const [selectedValue, setSelectedValue] = useState<string | undefined>(field.selected_value)
  const [newValue, setNewValue] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  const filteredValues = validValues.filter(v =>
    v.value.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleAddValue = async () => {
    if (!newValue.trim()) return

    setSaving(true)
    setError(null)
    try {
      const addedValue = await templatesApi.addFieldValue(field.id, newValue.trim())
      const newValidValues = [...validValues, addedValue]
      setValidValues(newValidValues)

      // UX Improvement: Backend auto-selects if it's the only value, update UI state
      let newSelectedValue = selectedValue
      if (newValidValues.length === 1) {
        newSelectedValue = addedValue.value
        setSelectedValue(newSelectedValue)
      }

      setNewValue('')
      setHasChanges(true)
      onUpdate({ ...field, valid_values: newValidValues, selected_value: newSelectedValue })
    } catch (err: any) {
      if (err.response?.data?.detail === 'Value already exists') {
        setError('This value already exists')
      } else {
        setError('Failed to add value')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteValue = async (valueId: number) => {
    setSaving(true)
    setError(null)
    try {
      const deletedValue = validValues.find(v => v.id === valueId)
      await templatesApi.deleteFieldValue(field.id, valueId)
      const newValidValues = validValues.filter(v => v.id !== valueId)
      setValidValues(newValidValues)
      setHasChanges(true)

      let newSelectedValue = selectedValue
      if (deletedValue && selectedValue === deletedValue.value) {
        newSelectedValue = undefined
      }

      // UX Improvement: Backend auto-selects if exactly one remains
      if (newValidValues.length === 1) {
        newSelectedValue = newValidValues[0].value
      } else if (newValidValues.length === 0) {
        newSelectedValue = undefined
      }

      if (newSelectedValue !== selectedValue) {
        setSelectedValue(newSelectedValue)
      }

      onUpdate({ ...field, valid_values: newValidValues, selected_value: newSelectedValue })
    } catch (err) {
      setError('Failed to delete value')
    } finally {
      setSaving(false)
    }
  }

  const handleSelectValue = async (value: string) => {
    const newSelected = selectedValue === value ? undefined : value
    setSaving(true)
    setError(null)
    try {
      await templatesApi.updateField(field.id, { selected_value: newSelected || '' })
      setSelectedValue(newSelected)
      setHasChanges(true)
      onUpdate({ ...field, valid_values: validValues, selected_value: newSelected })
    } catch (err) {
      setError('Failed to set selected value')
    } finally {
      setSaving(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAddValue()
    }
  }

  return (
    <Dialog
      open
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          resize: 'both',
          overflow: 'auto',
          minWidth: 400,
          minHeight: 300,
          maxWidth: '90vw',
          maxHeight: '90vh'
        }
      }}
    >
      <DialogTitle>
        Field Details: {field.field_name}
      </DialogTitle>
      <DialogContent dividers>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 3 }}>
          <Box>
            <Typography variant="subtitle2" color="text.secondary">Field Name</Typography>
            <Typography variant="body1">{field.field_name}</Typography>
          </Box>
          <Box>
            <Typography variant="subtitle2" color="text.secondary">Display Name</Typography>
            <Typography variant="body1">{field.display_name || '-'}</Typography>
          </Box>
          <Box>
            <Typography variant="subtitle2" color="text.secondary">Attribute Group</Typography>
            <Typography variant="body1">{field.attribute_group || '-'}</Typography>
          </Box>
          <Box>
            <Typography variant="subtitle2" color="text.secondary">Description</Typography>
            <Typography variant="body1">{field.description || '-'}</Typography>
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />

        <Box>
          <Typography variant="h6" gutterBottom>
            Valid Values ({validValues.length})
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {validValues.length > 0
              ? 'Click a value to set it as the default. If only one value exists, it’s selected automatically.'
              : 'This field accepts any value (no restrictions). Add values to create a dropdown list.'}
          </Typography>

          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <TextField
              size="small"
              placeholder="Add new value..."
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={saving}
              sx={{ flexGrow: 1 }}
            />
            <Button
              variant="contained"
              startIcon={saving ? <CircularProgress size={16} /> : <AddIcon />}
              onClick={handleAddValue}
              disabled={saving || !newValue.trim()}
            >
              Add
            </Button>
          </Box>

          {validValues.length > 0 && (
            <>
              <TextField
                size="small"
                placeholder="Search values..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                fullWidth
                sx={{ mb: 1 }}
              />
              {searchQuery && (
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                  Showing {filteredValues.length} of {validValues.length} values
                </Typography>
              )}
              <Box sx={{
                maxHeight: 300,
                overflowY: 'auto',
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
                p: 1
              }}>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {filteredValues.map((value) => (
                    <Chip
                      key={value.id}
                      label={value.value}
                      onClick={() => handleSelectValue(value.value)}
                      onDelete={() => handleDeleteValue(value.id)}
                      deleteIcon={<DeleteIcon />}
                      icon={selectedValue === value.value ? <CheckIcon /> : undefined}
                      color={selectedValue === value.value ? 'primary' : 'default'}
                      variant={selectedValue === value.value ? 'filled' : 'outlined'}
                      size="small"
                      sx={{ cursor: 'pointer' }}
                    />
                  ))}
                </Box>
              </Box>
            </>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>
          {hasChanges ? 'Done' : 'Close'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
