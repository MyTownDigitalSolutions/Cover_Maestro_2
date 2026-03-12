import { useEffect, useState } from 'react'
import {
  Box, Typography, Paper, Button, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, IconButton, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow,
  Chip, FormControl, InputLabel, Select, MenuItem, OutlinedInput, Checkbox, ListItemText
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import AddIcon from '@mui/icons-material/Add'
import SettingsIcon from '@mui/icons-material/Settings'
import DesignServicesIcon from '@mui/icons-material/DesignServices'
import { equipmentTypesApi, pricingApi, designOptionsApi, settingsApi, templatesApi, reverbTemplatesApi } from '../services/api'
import type { EquipmentTypeProductTypeLink } from '../services/api'
import type { EquipmentType, PricingOption, DesignOption, AmazonCustomizationTemplate, ReverbTemplateReference } from '../types'


export default function EquipmentTypesPage() {
  const [equipmentTypes, setEquipmentTypes] = useState<EquipmentType[]>([])
  const [allPricingOptions, setAllPricingOptions] = useState<PricingOption[]>([])
  const [allDesignOptions, setAllDesignOptions] = useState<DesignOption[]>([])
  const [equipmentTypePricingOptions, setEquipmentTypePricingOptions] = useState<Record<number, PricingOption[]>>({})
  const [equipmentTypeDesignOptions, setEquipmentTypeDesignOptions] = useState<Record<number, DesignOption[]>>({})
  const [dialogOpen, setDialogOpen] = useState(false)
  const [pricingDialogOpen, setPricingDialogOpen] = useState(false)
  const [designDialogOpen, setDesignDialogOpen] = useState(false)
  const [selectedEquipmentType, setSelectedEquipmentType] = useState<EquipmentType | null>(null)
  const [selectedPricingOptionIds, setSelectedPricingOptionIds] = useState<number[]>([])
  const [selectedDesignOptionIds, setSelectedDesignOptionIds] = useState<number[]>([])
  const [editing, setEditing] = useState<EquipmentType | null>(null)
  const [name, setName] = useState('')
  const [allCustomizationTemplates, setAllCustomizationTemplates] = useState<AmazonCustomizationTemplate[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)

  const [allReverbTemplates, setAllReverbTemplates] = useState<ReverbTemplateReference[]>([])
  const [selectedReverbTemplateId, setSelectedReverbTemplateId] = useState<number | null>(null)

  const [productTypeLinks, setProductTypeLinks] = useState<EquipmentTypeProductTypeLink[]>([])



  const loadEquipmentTypes = async () => {
    const data = await equipmentTypesApi.list()
    setEquipmentTypes(data)
    const pricingByType: Record<number, PricingOption[]> = {}
    const designByType: Record<number, DesignOption[]> = {}
    for (const et of data) {
      try {
        pricingByType[et.id] = await equipmentTypesApi.getPricingOptions(et.id)
      } catch {
        pricingByType[et.id] = []
      }
      try {
        designByType[et.id] = await equipmentTypesApi.getDesignOptions(et.id)
      } catch {
        designByType[et.id] = []
      }
    }
    setEquipmentTypePricingOptions(pricingByType)
    setEquipmentTypeDesignOptions(designByType)
  }

  const loadPricingOptions = async () => {
    const data = await pricingApi.listOptions()
    setAllPricingOptions(data)
  }

  const loadDesignOptions = async () => {
    const data = await designOptionsApi.list()
    setAllDesignOptions(data)
  }

  const loadCustomizationTemplates = async () => {
    const data = await settingsApi.listAmazonCustomizationTemplates()
    setAllCustomizationTemplates(data)
  }

  const loadProductTypeLinks = async () => {
    try {
      const data = await templatesApi.listEquipmentTypeLinks()
      setProductTypeLinks(data)
    } catch (e) {
      console.error('Failed to load equipment type links', e)
    }
  }

  const loadReverbTemplates = async () => {
    try {
      const data = await reverbTemplatesApi.list()
      setAllReverbTemplates(data)
    } catch (e) {
      console.error('Failed to load Reverb templates', e)
    }
  }

  useEffect(() => {
    loadEquipmentTypes()
    loadPricingOptions()
    loadDesignOptions()
    loadCustomizationTemplates()
    loadReverbTemplates()
    loadProductTypeLinks()
  }, [])

  const handleOpenDialog = async (equipmentType?: EquipmentType) => {
    await loadReverbTemplates()
    if (equipmentType) {
      setEditing(equipmentType)
      setName(equipmentType.name)
      setSelectedTemplateId(equipmentType.amazon_customization_template_id ?? null)
      setSelectedReverbTemplateId(equipmentType.reverb_template_id ?? null)
    } else {
      setEditing(null)
      setName('')
      setSelectedTemplateId(null)
      setSelectedReverbTemplateId(null)
    }
    setDialogOpen(true)
  }

  const handleSave = async () => {
    const data = { name }
    let savedId: number
    if (editing) {
      await equipmentTypesApi.update(editing.id, data)
      savedId = editing.id
    } else {
      const res = await equipmentTypesApi.create(data)
      savedId = res.id
    }

    // Assign template (always, even if null, to handle clearing)
    await settingsApi.assignAmazonCustomizationTemplate(savedId, selectedTemplateId)
    await settingsApi.assignReverbTemplate(savedId, selectedReverbTemplateId)

    setDialogOpen(false)
    loadEquipmentTypes()
  }

  const handleDelete = async (id: number) => {
    if (confirm('Are you sure you want to delete this equipment type?')) {
      await equipmentTypesApi.delete(id)
      loadEquipmentTypes()
    }
  }

  const handleOpenPricingDialog = (equipmentType: EquipmentType) => {
    setSelectedEquipmentType(equipmentType)
    const currentOptions = equipmentTypePricingOptions[equipmentType.id] || []
    setSelectedPricingOptionIds(currentOptions.map(o => o.id))
    setPricingDialogOpen(true)
  }

  const handleSavePricingOptions = async () => {
    if (!selectedEquipmentType) return
    await equipmentTypesApi.setPricingOptions(selectedEquipmentType.id, selectedPricingOptionIds)
    setPricingDialogOpen(false)
    loadEquipmentTypes()
  }

  const handleOpenDesignDialog = (equipmentType: EquipmentType) => {
    setSelectedEquipmentType(equipmentType)
    const currentOptions = equipmentTypeDesignOptions[equipmentType.id] || []
    setSelectedDesignOptionIds(currentOptions.map(o => o.id))
    setDesignDialogOpen(true)
  }

  const handleSaveDesignOptions = async () => {
    if (!selectedEquipmentType) return
    await equipmentTypesApi.setDesignOptions(selectedEquipmentType.id, selectedDesignOptionIds)
    setDesignDialogOpen(false)
    loadEquipmentTypes()
  }



  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Equipment Types</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => void handleOpenDialog()}
        >
          Add Equipment Type
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Design Options</TableCell>
              <TableCell>Pricing Options</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {equipmentTypes.map((et) => (
              <TableRow key={et.id}>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>{et.name}</Typography>
                  <Box sx={{ mt: 0.5, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {(() => {
                      const assigned = productTypeLinks.some(l => l.equipment_type_id === et.id)
                      return (
                        <Chip
                          label={`Amazon Product Type: ${assigned ? 'Assigned' : 'Not assigned'}`}
                          size="small"
                          color={assigned ? 'success' : 'default'}
                          variant="outlined"
                        />
                      )
                    })()}
                    {(() => {
                      const assigned = !!(et as any).amazon_customization_template_id
                      return (
                        <Chip
                          label={`Amazon Customization: ${assigned ? 'Assigned' : 'Not assigned'}`}
                          size="small"
                          color={assigned ? 'success' : 'default'}
                          variant="outlined"
                        />
                      )
                    })()}
                    {(() => {
                      const assigned = !!(et as any).reverb_template_id
                      return (
                        <Chip
                          label={`Reverb Template: ${assigned ? 'Assigned' : 'Not assigned'}`}
                          size="small"
                          color={assigned ? 'success' : 'default'}
                          variant="outlined"
                        />
                      )
                    })()}
                  </Box>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {(equipmentTypeDesignOptions[et.id] || []).map((option) => (
                      <Chip key={option.id} label={option.name} size="small" color="primary" variant="outlined" />
                    ))}
                    {(!equipmentTypeDesignOptions[et.id] || equipmentTypeDesignOptions[et.id].length === 0) && (
                      <Typography variant="body2" color="text.secondary">None</Typography>
                    )}
                  </Box>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {(equipmentTypePricingOptions[et.id] || []).map((option) => (
                      <Chip key={option.id} label={option.name} size="small" />
                    ))}
                    {(!equipmentTypePricingOptions[et.id] || equipmentTypePricingOptions[et.id].length === 0) && (
                      <Typography variant="body2" color="text.secondary">None</Typography>
                    )}
                  </Box>
                </TableCell>
                <TableCell align="right">

                  <IconButton onClick={() => handleOpenDesignDialog(et)} size="small" title="Manage Design Options">
                    <DesignServicesIcon />
                  </IconButton>
                  <IconButton onClick={() => handleOpenPricingDialog(et)} size="small" title="Manage Pricing Options">
                    <SettingsIcon />
                  </IconButton>
                  <IconButton onClick={() => void handleOpenDialog(et)} size="small">
                    <EditIcon />
                  </IconButton>
                  <IconButton onClick={() => handleDelete(et.id)} size="small" color="error">
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {equipmentTypes.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  No equipment types found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? 'Edit Equipment Type' : 'Add Equipment Type'}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Name"
            fullWidth
            value={name}
            onChange={(e) => setName(e.target.value)}
            sx={{ mb: 2 }}
          />

          <FormControl fullWidth margin="dense">
            <InputLabel id="template-select-label">Amazon Customization Template</InputLabel>
            <Select
              labelId="template-select-label"
              value={selectedTemplateId || ''}
              onChange={(e) => setSelectedTemplateId(e.target.value === '' ? null : Number(e.target.value))}
              input={<OutlinedInput label="Amazon Customization Template" />}
            >
              <MenuItem value="">
                <em>None</em>
              </MenuItem>
              {allCustomizationTemplates.map((template) => (
                <MenuItem key={template.id} value={template.id}>
                  {template.original_filename}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth margin="dense">
            <InputLabel id="reverb-template-select-label">Reverb Template</InputLabel>
            <Select
              labelId="reverb-template-select-label"
              value={selectedReverbTemplateId || ''}
              onChange={(e) => setSelectedReverbTemplateId(e.target.value === '' ? null : Number(e.target.value))}
              input={<OutlinedInput label="Reverb Template" />}
            >
              <MenuItem value="">
                <em>None</em>
              </MenuItem>
              {allReverbTemplates.map((template) => (
                <MenuItem key={template.id} value={template.id}>
                  {template.original_filename}
                </MenuItem>
              ))}
            </Select>
          </FormControl>


        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={!name.trim()}>
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={pricingDialogOpen} onClose={() => setPricingDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Manage Pricing Options for {selectedEquipmentType?.name}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Select the pricing add-ons that apply to this equipment type.
          </Typography>
          <FormControl fullWidth sx={{ mt: 1 }}>
            <InputLabel>Pricing Options</InputLabel>
            <Select
              multiple
              value={selectedPricingOptionIds}
              onChange={(e) => setSelectedPricingOptionIds(e.target.value as number[])}
              input={<OutlinedInput label="Pricing Options" />}
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((id) => {
                    const option = allPricingOptions.find(o => o.id === id)
                    return option ? <Chip key={id} label={option.name} size="small" /> : null
                  })}
                </Box>
              )}
            >
              {allPricingOptions.map((option) => (
                <MenuItem key={option.id} value={option.id}>
                  <Checkbox checked={selectedPricingOptionIds.includes(option.id)} />
                  <ListItemText primary={option.name} secondary={`$${option.price.toFixed(2)}`} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPricingDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSavePricingOptions} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={designDialogOpen} onClose={() => setDesignDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Manage Design Options for {selectedEquipmentType?.name}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Select the design features that apply to this equipment type (e.g., Handle Options, Angle Options).
          </Typography>
          <FormControl fullWidth sx={{ mt: 1 }}>
            <InputLabel>Design Options</InputLabel>
            <Select
              multiple
              value={selectedDesignOptionIds}
              onChange={(e) => setSelectedDesignOptionIds(e.target.value as number[])}
              input={<OutlinedInput label="Design Options" />}
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((id) => {
                    const option = allDesignOptions.find(o => o.id === id)
                    return option ? <Chip key={id} label={option.name} size="small" color="primary" variant="outlined" /> : null
                  })}
                </Box>
              )}
            >
              {allDesignOptions.map((option) => (
                <MenuItem key={option.id} value={option.id}>
                  <Checkbox checked={selectedDesignOptionIds.includes(option.id)} />
                  <ListItemText primary={option.name} secondary={option.description} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDesignDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveDesignOptions} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>


    </Box>
  )
}
