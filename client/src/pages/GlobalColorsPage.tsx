import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import type { CanonicalColor } from '../types'
import { colorsApi } from '../services/api'

type ColorFormState = {
  internal_name: string
  friendly_name: string
  sku_abbrev: string
  is_active: boolean
}

const emptyForm: ColorFormState = {
  internal_name: '',
  friendly_name: '',
  sku_abbrev: '',
  is_active: true,
}

export default function GlobalColorsPage() {
  const [colors, setColors] = useState<CanonicalColor[]>([])
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState<ColorFormState>(emptyForm)

  const [editOpen, setEditOpen] = useState(false)
  const [editingColor, setEditingColor] = useState<CanonicalColor | null>(null)
  const [editForm, setEditForm] = useState<ColorFormState>(emptyForm)

  const sortedColors = useMemo(
    () => [...colors].sort((a, b) => a.friendly_name.localeCompare(b.friendly_name) || a.id - b.id),
    [colors]
  )

  const loadColors = async () => {
    try {
      const data = await colorsApi.list()
      setColors(data)
      setError(null)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load colors')
    }
  }

  useEffect(() => {
    loadColors()
  }, [])

  const validateForm = (form: ColorFormState): string | null => {
    if (!form.internal_name || !form.internal_name.trim()) return 'internal_name is required'
    if (!form.friendly_name || !form.friendly_name.trim()) return 'friendly_name is required'
    if (!form.sku_abbrev || !form.sku_abbrev.trim()) return 'sku_abbrev is required'
    return null
  }

  const handleCreate = async () => {
    const validationError = validateForm(createForm)
    if (validationError) {
      setError(validationError)
      return
    }
    setSaving(true)
    try {
      await colorsApi.create(createForm)
      setCreateOpen(false)
      setCreateForm(emptyForm)
      await loadColors()
      setError(null)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create color')
    } finally {
      setSaving(false)
    }
  }

  const openEditDialog = (color: CanonicalColor) => {
    setEditingColor(color)
    setEditForm({
      internal_name: color.internal_name,
      friendly_name: color.friendly_name,
      sku_abbrev: color.sku_abbrev,
      is_active: color.is_active,
    })
    setEditOpen(true)
  }

  const handleEditSave = async () => {
    if (!editingColor) return
    const validationError = validateForm(editForm)
    if (validationError) {
      setError(validationError)
      return
    }
    setSaving(true)
    try {
      await colorsApi.update(editingColor.id, editForm)
      setEditOpen(false)
      setEditingColor(null)
      await loadColors()
      setError(null)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update color')
    } finally {
      setSaving(false)
    }
  }

  const handleToggleActive = async (color: CanonicalColor) => {
    setSaving(true)
    try {
      await colorsApi.update(color.id, { is_active: !color.is_active })
      await loadColors()
      setError(null)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to toggle color active state')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Global Colors</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateOpen(true)}
          disabled={saving}
        >
          New Color
        </Button>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="body2" color="text.secondary">
          Manage canonical colors used across the system. This page edits only global rows in the
          canonical colors table.
        </Typography>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Internal Name</TableCell>
              <TableCell>Friendly Name</TableCell>
              <TableCell>SKU Abbrev</TableCell>
              <TableCell align="center">Active</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedColors.map((color) => (
              <TableRow key={color.id}>
                <TableCell>{color.internal_name}</TableCell>
                <TableCell>{color.friendly_name}</TableCell>
                <TableCell>{color.sku_abbrev}</TableCell>
                <TableCell align="center">
                  <Checkbox
                    checked={color.is_active}
                    onChange={() => handleToggleActive(color)}
                    disabled={saving}
                  />
                </TableCell>
                <TableCell align="right">
                  <Button
                    size="small"
                    startIcon={<EditIcon />}
                    onClick={() => openEditDialog(color)}
                    disabled={saving}
                  >
                    Edit
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {sortedColors.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  No canonical colors found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Create Color</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <TextField
            fullWidth
            margin="dense"
            label="Internal Name"
            value={createForm.internal_name}
            onChange={(e) => setCreateForm({ ...createForm, internal_name: e.target.value })}
          />
          <TextField
            fullWidth
            margin="dense"
            label="Friendly Name"
            value={createForm.friendly_name}
            onChange={(e) => setCreateForm({ ...createForm, friendly_name: e.target.value })}
          />
          <TextField
            fullWidth
            margin="dense"
            label="SKU Abbrev"
            value={createForm.sku_abbrev}
            onChange={(e) => setCreateForm({ ...createForm, sku_abbrev: e.target.value })}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={createForm.is_active}
                onChange={(e) => setCreateForm({ ...createForm, is_active: e.target.checked })}
              />
            }
            label="Active"
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)} disabled={saving}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained" disabled={saving}>Create</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Edit Color</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <TextField
            fullWidth
            margin="dense"
            label="Internal Name"
            value={editForm.internal_name}
            onChange={(e) => setEditForm({ ...editForm, internal_name: e.target.value })}
          />
          <TextField
            fullWidth
            margin="dense"
            label="Friendly Name"
            value={editForm.friendly_name}
            onChange={(e) => setEditForm({ ...editForm, friendly_name: e.target.value })}
          />
          <TextField
            fullWidth
            margin="dense"
            label="SKU Abbrev"
            value={editForm.sku_abbrev}
            onChange={(e) => setEditForm({ ...editForm, sku_abbrev: e.target.value })}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={editForm.is_active}
                onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
              />
            }
            label="Active"
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)} disabled={saving}>Cancel</Button>
          <Button onClick={handleEditSave} variant="contained" disabled={saving}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
