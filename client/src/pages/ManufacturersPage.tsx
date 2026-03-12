import { useEffect, useState, useRef, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Box, Typography, Paper, Button, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, IconButton, List, ListItem, ListItemText,
  ListItemSecondaryAction, Autocomplete, Stack
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import AddIcon from '@mui/icons-material/Add'
import { manufacturersApi, seriesApi } from '../services/api'
import type { Manufacturer, Series } from '../types'

export default function ManufacturersPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [manufacturers, setManufacturers] = useState<Manufacturer[]>([])
  const [series, setSeries] = useState<Series[]>([])
  const [selectedManufacturer, setSelectedManufacturer] = useState<Manufacturer | null>(null)
  const [selectedSeries, setSelectedSeries] = useState<Series | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [seriesDialogOpen, setSeriesDialogOpen] = useState(false)
  const [editingManufacturer, setEditingManufacturer] = useState<Manufacturer | null>(null)
  const [editingSeries, setEditingSeries] = useState<Series | null>(null)
  const [name, setName] = useState('')
  const [seriesName, setSeriesName] = useState('')
  const lastManufacturerDialogTriggerRef = useRef<HTMLElement | null>(null)
  const lastSeriesDialogTriggerRef = useRef<HTMLElement | null>(null)
  const manufacturerNameInputRef = useRef<HTMLInputElement | null>(null)
  const seriesNameInputRef = useRef<HTMLInputElement | null>(null)

  // Restore focus on dialog close
  useEffect(() => {
    if (!dialogOpen && lastManufacturerDialogTriggerRef.current) {
      const el = lastManufacturerDialogTriggerRef.current
      requestAnimationFrame(() => el.focus())
    }
  }, [dialogOpen])

  useEffect(() => {
    if (!seriesDialogOpen && lastSeriesDialogTriggerRef.current) {
      const el = lastSeriesDialogTriggerRef.current
      requestAnimationFrame(() => el.focus())
    }
  }, [seriesDialogOpen])

  // Delete confirmation states
  const [deleteManufacturerOpen, setDeleteManufacturerOpen] = useState(false)
  const [manufacturerToDelete, setManufacturerToDelete] = useState<number | null>(null)

  const [deleteSeriesOpen, setDeleteSeriesOpen] = useState(false)
  const [seriesToDelete, setSeriesToDelete] = useState<Series | null>(null)

  const loadManufacturers = async () => {
    const data = await manufacturersApi.list()
    setManufacturers(data)
  }

  const loadSeries = async (manufacturerId: number) => {
    const data = await seriesApi.list(manufacturerId)
    setSeries(data)
  }

  useEffect(() => {
    loadManufacturers()
  }, [])

  useEffect(() => {
    if (selectedManufacturer) {
      loadSeries(selectedManufacturer.id)
    } else {
      setSeries([])
    }
    setSelectedSeries(null)
  }, [selectedManufacturer])

  useEffect(() => {
    const mid = searchParams.get('manufacturerId')
    if (mid && manufacturers.length > 0 && !selectedManufacturer) {
      const m = manufacturers.find(x => x.id === Number(mid))
      if (m) setSelectedManufacturer(m)
    }
  }, [manufacturers, searchParams, selectedManufacturer])

  useEffect(() => {
    const sid = searchParams.get('seriesId')
    if (sid && series.length > 0 && !selectedSeries) {
      const s = series.find(x => x.id === Number(sid))
      if (s) setSelectedSeries(s)
    }
  }, [series, searchParams, selectedSeries])

  const handleSave = async () => {
    if (editingManufacturer) {
      await manufacturersApi.update(editingManufacturer.id, { name })
    } else {
      await manufacturersApi.create({ name })
    }
    setDialogOpen(false)
    setName('')
    setEditingManufacturer(null)
    loadManufacturers()
  }

  const handleDeleteManufacturerClick = (id: number) => {
    setManufacturerToDelete(id)
    setDeleteManufacturerOpen(true)
  }

  const handleConfirmDeleteManufacturer = async () => {
    if (manufacturerToDelete !== null) {
      await manufacturersApi.delete(manufacturerToDelete)
      loadManufacturers()
      if (selectedManufacturer?.id === manufacturerToDelete) {
        setSelectedManufacturer(null)
        setSeries([])
      }
      setDeleteManufacturerOpen(false)
      setManufacturerToDelete(null)
    }
  }

  const handleAddSeries = () => {
    setEditingSeries(null)
    setSeriesName('')
    setSeriesDialogOpen(true)
  }

  const handleSaveSeries = async () => {
    if (selectedManufacturer) {
      if (editingSeries) {
        await seriesApi.update(editingSeries.id, { name: seriesName, manufacturer_id: selectedManufacturer.id })
      } else {
        await seriesApi.create({ name: seriesName, manufacturer_id: selectedManufacturer.id })
      }
      setSeriesDialogOpen(false)
      setSeriesName('')
      setEditingSeries(null)
      loadSeries(selectedManufacturer.id)
    }
  }



  const handleDeleteSeriesClick = (series: Series) => {
    setSeriesToDelete(series)
    setDeleteSeriesOpen(true)
  }

  const handleConfirmDeleteSeries = async () => {
    if (seriesToDelete) {
      try {
        await seriesApi.delete(seriesToDelete.id)
        if (selectedManufacturer) {
          loadSeries(selectedManufacturer.id)
        }
        setDeleteSeriesOpen(false)
        setSeriesToDelete(null)
      } catch (error: any) {
        console.error("Failed to delete series:", error)
        if (error.response && error.response.status === 400) {
          alert(error.response.data.detail)
        } else {
          alert("An error occurred while deleting the series.")
        }
        setDeleteSeriesOpen(false) // Close dialog even on error so user can acknowledge alert
      }
    }
  }

  const sortedManufacturers = useMemo(() => {
    return [...manufacturers].sort((a, b) => (a.name || '').localeCompare(b.name || ''))
  }, [manufacturers])

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Manufacturers & Series</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={(e) => {
            lastManufacturerDialogTriggerRef.current = e.currentTarget
            setEditingManufacturer(null)
            setName('')
            setDialogOpen(true)
          }}
        >
          Add Manufacturer
        </Button>
      </Box>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <Autocomplete
            options={sortedManufacturers}
            getOptionLabel={(option) => option.name}
            value={selectedManufacturer}
            onChange={(_, newValue) => setSelectedManufacturer(newValue)}
            renderInput={(params) => <TextField {...params} label="Select Manufacturer" />}
            sx={{ width: 300 }}
          />
          <IconButton
            disabled={!selectedManufacturer}
            onClick={() => {
              if (selectedManufacturer) {
                setEditingManufacturer(selectedManufacturer)
                setName(selectedManufacturer.name)
                setDialogOpen(true)
              }
            }}
          >
            <EditIcon />
          </IconButton>
          <IconButton
            disabled={!selectedManufacturer}
            onClick={() => selectedManufacturer && handleDeleteManufacturerClick(selectedManufacturer.id)}
            color="error"
          >
            <DeleteIcon />
          </IconButton>
        </Stack>
        {!selectedManufacturer && (
          <Typography color="text.secondary" sx={{ mt: 2 }}>
            Select a manufacturer to view its series.
          </Typography>
        )}
      </Paper>

      {selectedManufacturer && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Series for {selectedManufacturer.name}
            </Typography>
            <Button
              size="small"
              startIcon={<AddIcon />}
              onClick={(e) => {
                lastSeriesDialogTriggerRef.current = e.currentTarget
                handleAddSeries()
              }}
            >
              Add Series
            </Button>
          </Box>
          <List>
            {series.map((s) => (
              <ListItem
                key={s.id}
                button
                selected={selectedSeries?.id === s.id}
                onClick={() => setSelectedSeries(s)}
              >
                <ListItemText primary={s.name} />
                <ListItemSecondaryAction>
                  <IconButton
                    edge="end"
                    onClick={(e) => {
                      e.stopPropagation()
                      setEditingSeries(s)
                      setSeriesName(s.name)
                      setSeriesDialogOpen(true)
                    }}
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton edge="end" onClick={() => handleDeleteSeriesClick(s)}>
                    <DeleteIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
            {series.length === 0 && (
              <Typography color="text.secondary" sx={{ p: 2 }}>
                No series found. Add one to get started.
              </Typography>
            )}
          </List>
        </Paper>
      )}

      {selectedManufacturer && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>Models</Typography>
          <Typography sx={{ mb: 2 }}>
            {selectedSeries
              ? <>Manage models for <strong>{selectedSeries.name}</strong>.</>
              : <>Manage all models for <strong>{selectedManufacturer.name}</strong>.</>
            }
          </Typography>
          <Button variant="outlined" onClick={() => {
            const url = selectedSeries
              ? `/models?manufacturerId=${selectedManufacturer.id}&seriesId=${selectedSeries.id}`
              : `/models?manufacturerId=${selectedManufacturer.id}`
            navigate(url)
          }}>
            Go to Models Page
          </Button>
        </Paper>
      )}

      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        TransitionProps={{ onEntered: () => manufacturerNameInputRef.current?.focus() }}
      >
        <DialogTitle>
          {editingManufacturer ? 'Edit Manufacturer' : 'Add Manufacturer'}
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            inputRef={manufacturerNameInputRef}
            margin="dense"
            label="Name"
            fullWidth
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSave()
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={seriesDialogOpen}
        onClose={() => setSeriesDialogOpen(false)}
        TransitionProps={{ onEntered: () => seriesNameInputRef.current?.focus() }}
      >
        <DialogTitle>{editingSeries ? 'Edit Series' : 'Add Series'}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            inputRef={seriesNameInputRef}
            margin="dense"
            label="Series Name"
            fullWidth
            value={seriesName}
            onChange={(e) => setSeriesName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSaveSeries()
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSeriesDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveSeries} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Manufacturer Confirmation Dialog */}
      <Dialog
        open={deleteManufacturerOpen}
        onClose={() => setDeleteManufacturerOpen(false)}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this manufacturer? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteManufacturerOpen(false)}>Cancel</Button>
          <Button onClick={handleConfirmDeleteManufacturer} color="error" variant="contained" autoFocus>
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Series Confirmation Dialog */}
      <Dialog
        open={deleteSeriesOpen}
        onClose={() => setDeleteSeriesOpen(false)}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete the series "{seriesToDelete?.name}"? {seriesToDelete && 'This action cannot be undone.'}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteSeriesOpen(false)}>Cancel</Button>
          <Button onClick={handleConfirmDeleteSeries} color="error" variant="contained" autoFocus>
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
