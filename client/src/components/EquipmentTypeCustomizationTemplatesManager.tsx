import { useState, useEffect } from 'react'
import {
    Box, Typography, Paper, Button, IconButton, Dialog, DialogTitle,
    DialogContent, DialogActions, FormControl, InputLabel, Select, MenuItem,
    OutlinedInput, Radio, RadioGroup, FormControlLabel, Alert
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import StarIcon from '@mui/icons-material/Star'
import StarOutlineIcon from '@mui/icons-material/StarOutline'
import AddIcon from '@mui/icons-material/Add'
import { settingsApi } from '../services/api'
import type { AmazonCustomizationTemplate, EquipmentTypeCustomizationTemplateItem } from '../types'

export default function EquipmentTypeCustomizationTemplatesManager({
    equipmentTypeId,
    equipmentTypeName
}: { equipmentTypeId: number, equipmentTypeName: string }) {
    const [assignedTemplates, setAssignedTemplates] = useState<EquipmentTypeCustomizationTemplateItem[]>([])
    const [defaultTemplateId, setDefaultTemplateId] = useState<number | null>(null)
    const [allTemplates, setAllTemplates] = useState<AmazonCustomizationTemplate[]>([])
    const [assignDialogOpen, setAssignDialogOpen] = useState(false)
    const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)
    const [selectedSlot, setSelectedSlot] = useState<number>(1)
    const [error, setError] = useState<string | null>(null)

    const loadData = async () => {
        if (!equipmentTypeId) return

        try {
            setError(null)
            const [templatesResp, allTemplatesResp] = await Promise.all([
                settingsApi.listEquipmentTypeCustomizationTemplates(equipmentTypeId),
                settingsApi.listAmazonCustomizationTemplates()
            ])
            setAssignedTemplates(templatesResp.templates)
            setDefaultTemplateId(templatesResp.default_template_id)
            setAllTemplates(allTemplatesResp)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load templates')
            console.error('Error loading templates:', err)
        }
    }

    useEffect(() => {
        loadData()
    }, [equipmentTypeId])

    const handleSetDefault = async (templateId: number) => {
        try {
            setError(null)
            await settingsApi.setEquipmentTypeCustomizationTemplateDefault(equipmentTypeId, templateId)
            setDefaultTemplateId(templateId)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to set default template')
            console.error('Error setting default:', err)
        }
    }

    const handleUnassign = async (templateId: number) => {
        if (!confirm('Remove this template from the equipment type?')) return
        try {
            setError(null)
            await settingsApi.unassignEquipmentTypeCustomizationTemplate(equipmentTypeId, templateId)
            await loadData()
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to unassign template')
            console.error('Error unassigning:', err)
        }
    }

    const handleOpenAssignDialog = () => {
        // Find first available slot
        const usedSlots = new Set(assignedTemplates.map(t => t.slot))
        const availableSlot = [1, 2, 3].find(s => !usedSlots.has(s)) || 1
        setSelectedSlot(availableSlot)
        setSelectedTemplateId(null)
        setAssignDialogOpen(true)
    }

    const handleAssign = async () => {
        if (!selectedTemplateId) return

        // Check if slot is occupied
        const existingInSlot = assignedTemplates.find(t => t.slot === selectedSlot)
        if (existingInSlot) {
            if (!confirm(`Replace template in slot ${selectedSlot}?`)) return
        }

        try {
            setError(null)
            await settingsApi.assignEquipmentTypeCustomizationTemplate(equipmentTypeId, selectedTemplateId, selectedSlot)
            setAssignDialogOpen(false)
            await loadData()
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to assign template')
            console.error('Error assigning:', err)
        }
    }

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        })
    }

    return (
        <Box>
            {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            <Typography variant="subtitle2" gutterBottom>
                Customization Slots for {equipmentTypeName}
            </Typography>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                The default template is used automatically during export unless overridden.
            </Typography>

            {assignedTemplates.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4, border: '1px dashed #ccc', borderRadius: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                        No templates assigned to slots
                    </Typography>
                </Box>
            ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {assignedTemplates.sort((a, b) => a.slot - b.slot).map((template) => (
                        <Paper key={template.template_id} variant="outlined" sx={{ p: 2 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                <Box sx={{
                                    bgcolor: 'primary.main',
                                    color: 'white',
                                    borderRadius: 1,
                                    px: 1.5,
                                    py: 0.5,
                                    fontWeight: 'bold',
                                    fontSize: '0.875rem'
                                }}>
                                    Slot {template.slot}
                                </Box>
                                <Box sx={{ flex: 1 }}>
                                    <Typography variant="body1">
                                        {template.original_filename}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        Uploaded: {formatDate(template.upload_date)}
                                    </Typography>
                                </Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <IconButton
                                        size="small"
                                        onClick={() => handleSetDefault(template.template_id)}
                                        disabled={defaultTemplateId === template.template_id}
                                        title={defaultTemplateId === template.template_id ? 'Current default' : 'Set as default'}
                                        color={defaultTemplateId === template.template_id ? 'primary' : 'default'}
                                    >
                                        {defaultTemplateId === template.template_id ? <StarIcon /> : <StarOutlineIcon />}
                                    </IconButton>
                                    <IconButton
                                        size="small"
                                        onClick={() => handleUnassign(template.template_id)}
                                        color="error"
                                        title="Remove"
                                    >
                                        <DeleteIcon />
                                    </IconButton>
                                </Box>
                            </Box>
                        </Paper>
                    ))}
                </Box>
            )}

            {assignedTemplates.length < 3 && (
                <Button
                    variant="outlined"
                    startIcon={<AddIcon />}
                    onClick={handleOpenAssignDialog}
                    sx={{ mt: 2 }}
                    fullWidth
                >
                    Assign Template to Slot
                </Button>
            )}

            {assignedTemplates.length > 0 && !defaultTemplateId && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                    No default selected. Select a default template to use during export.
                </Alert>
            )}

            <Dialog open={assignDialogOpen} onClose={() => setAssignDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Assign Template</DialogTitle>
                <DialogContent>
                    <FormControl fullWidth margin="dense" sx={{ mt: 1 }}>
                        <InputLabel>Template</InputLabel>
                        <Select
                            value={selectedTemplateId || ''}
                            onChange={(e) => setSelectedTemplateId(e.target.value === '' ? null : Number(e.target.value))}
                            input={<OutlinedInput label="Template" />}
                        >
                            <MenuItem value="">
                                <em>Select a template</em>
                            </MenuItem>
                            {allTemplates.map((template) => {
                                // Check if template is already assigned to another slot
                                const alreadyAssigned = assignedTemplates.find(t => t.template_id === template.id && t.slot !== selectedSlot)
                                return (
                                    <MenuItem
                                        key={template.id}
                                        value={template.id}
                                        disabled={!!alreadyAssigned}
                                    >
                                        {template.original_filename}
                                        {alreadyAssigned && <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>(in slot {alreadyAssigned.slot})</Typography>}
                                    </MenuItem>
                                )
                            })}
                        </Select>
                    </FormControl>

                    <FormControl component="fieldset" sx={{ mt: 2 }}>
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>Slot</Typography>
                        <RadioGroup
                            row
                            value={selectedSlot}
                            onChange={(e) => setSelectedSlot(Number(e.target.value))}
                        >
                            {[1, 2, 3].map((slot) => {
                                const slotOccupied = assignedTemplates.find(t => t.slot === slot)
                                return (
                                    <FormControlLabel
                                        key={slot}
                                        value={slot}
                                        control={<Radio />}
                                        label={
                                            slotOccupied
                                                ? `Slot ${slot} (${slotOccupied.original_filename})`
                                                : `Slot ${slot}`
                                        }
                                    />
                                )
                            })}
                        </RadioGroup>
                    </FormControl>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setAssignDialogOpen(false)}>Cancel</Button>
                    <Button onClick={handleAssign} variant="contained" disabled={!selectedTemplateId}>
                        Assign
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}
