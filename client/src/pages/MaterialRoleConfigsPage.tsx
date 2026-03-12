import { useEffect, useState } from 'react'
import {
    Box, Typography, Paper, Button, TextField, IconButton, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, Checkbox, Alert
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import SaveIcon from '@mui/icons-material/Save'
import { apiClient } from '../services/api'
import { formatMaterialRoleLabel } from '../utils/materialRoleLabels'

interface MaterialRoleConfig {
    id: number
    role: string
    display_name: string | null
    display_name_with_padding: string | null
    sku_abbrev_no_padding: string | null
    sku_abbrev_with_padding: string | null
    ebay_variation_enabled: boolean
    sort_order: number
    created_at?: string
    updated_at?: string
}

export default function MaterialRoleConfigsPage() {
    const [configs, setConfigs] = useState<MaterialRoleConfig[]>([])
    const [newRow, setNewRow] = useState<Partial<MaterialRoleConfig> | null>(null)
    const [error, setError] = useState<string | null>(null)

    // Helper to safely convert values to string
    const asString = (v: any) => (v ?? '').toString()

    const loadData = async () => {
        try {
            const response = await apiClient.get<MaterialRoleConfig[]>('/material-role-configs')
            setConfigs(response.data)
            setError(null)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load material role configs')
        }
    }

    useEffect(() => {
        loadData()
    }, [])

    const handleAddNew = () => {
        setNewRow({
            role: '',
            display_name: '',
            display_name_with_padding: '',
            sku_abbrev_no_padding: '',
            sku_abbrev_with_padding: '',
            ebay_variation_enabled: false,
            sort_order: 0
        })
    }

    const handleSaveNew = async () => {
        if (!newRow || !newRow.role?.trim()) {
            setError('Role is required')
            return
        }

        // Validation
        if (newRow.sku_abbrev_no_padding && newRow.sku_abbrev_no_padding.length > 4) {
            setError('SKU abbreviation (no padding) must be 4 characters or less')
            return
        }
        if (newRow.sku_abbrev_with_padding && newRow.sku_abbrev_with_padding.length > 4) {
            setError('SKU abbreviation (with padding) must be 4 characters or less')
            return
        }
        if (newRow.sort_order !== undefined && newRow.sort_order < 0) {
            setError('Sort order cannot be negative')
            return
        }

        try {
            // Force role to uppercase, convert empty strings to null
            const payload = {
                role: newRow.role.trim().toUpperCase(),
                display_name: newRow.display_name?.trim() || null,
                display_name_with_padding: newRow.display_name_with_padding?.trim() || null,
                sku_abbrev_no_padding: newRow.sku_abbrev_no_padding?.trim() || null,
                sku_abbrev_with_padding: newRow.sku_abbrev_with_padding?.trim() || null,
                ebay_variation_enabled: newRow.ebay_variation_enabled || false,
                sort_order: newRow.sort_order ?? 0
            }
            await apiClient.post('/material-role-configs', payload)
            setNewRow(null)
            setError(null)
            loadData()
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create role config')
        }
    }

    const handleCancelNew = () => {
        setNewRow(null)
        setError(null)
    }

    const handleUpdateField = async (id: number, field: keyof MaterialRoleConfig, value: any) => {
        // Find the current config
        const config = configs.find(c => c.id === id)
        if (!config) return

        // Normalize the new value based on field type
        let normalizedValue: any

        if (field === 'display_name' || field === 'display_name_with_padding') {
            normalizedValue = asString(value).trim() || null
        } else if (field === 'sku_abbrev_no_padding' || field === 'sku_abbrev_with_padding') {
            normalizedValue = asString(value).trim().toUpperCase() || null
        } else if (field === 'sort_order') {
            const parsed = parseInt(value)
            if (isNaN(parsed)) {
                normalizedValue = 0
            } else if (parsed < 0) {
                setError('Sort order cannot be negative')
                loadData() // Reload to revert UI
                return
            } else {
                normalizedValue = parsed
            }
        } else if (field === 'ebay_variation_enabled') {
            normalizedValue = value
        } else {
            normalizedValue = value
        }

        // Check if value actually changed
        if (normalizedValue === config[field]) {
            return // No change, skip API call
        }

        try {
            const payload = { [field]: normalizedValue }
            await apiClient.put(`/material-role-configs/${id}`, payload)
            setError(null)
            loadData()
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update role config')
            loadData() // Reload to revert UI
        }
    }

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure you want to delete this material role config?')) return

        try {
            await apiClient.delete(`/material-role-configs/${id}`)
            setError(null)
            loadData()
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to delete role config')
        }
    }

    return (
        <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
                <Typography variant="h4">Material Role Configs</Typography>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleAddNew}
                    disabled={newRow !== null}
                >
                    New Role Config
                </Button>
            </Box>

            <Paper sx={{ p: 2, mb: 3 }}>
                <Typography variant="body2" color="text.secondary">
                    Material role configs define role-level SKU abbreviations for eBay variation generation.
                    Each role (e.g., CHOICE_WATERPROOF_FABRIC) has abbreviations that are used instead of material-specific codes.
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
                            <TableCell>Role</TableCell>
                            <TableCell>Display Name</TableCell>
                            <TableCell>Display Name (With Padding)</TableCell>
                            <TableCell>SKU Abbrev (No Padding)</TableCell>
                            <TableCell>SKU Abbrev (With Padding)</TableCell>
                            <TableCell align="center">eBay Enabled</TableCell>
                            <TableCell align="center">Sort Order</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {/* New Row */}
                        {newRow && (
                            <TableRow>
                                <TableCell>
                                    <TextField
                                        size="small"
                                        fullWidth
                                        value={newRow.role || ''}
                                        onChange={(e) => setNewRow({ ...newRow, role: e.target.value })}
                                        placeholder="choice_waterproof_fabric"
                                        required
                                    />
                                </TableCell>
                                <TableCell>
                                    <TextField
                                        size="small"
                                        fullWidth
                                        value={newRow.display_name || ''}
                                        onChange={(e) => setNewRow({ ...newRow, display_name: e.target.value })}
                                        placeholder="Choice Waterproof Fabric"
                                    />
                                </TableCell>
                                <TableCell>
                                    <TextField
                                        size="small"
                                        fullWidth
                                        value={newRow.display_name_with_padding || ''}
                                        onChange={(e) => setNewRow({ ...newRow, display_name_with_padding: e.target.value })}
                                        placeholder="Choice Waterproof Fabric w/ padding"
                                    />
                                </TableCell>
                                <TableCell>
                                    <TextField
                                        size="small"
                                        fullWidth
                                        value={newRow.sku_abbrev_no_padding || ''}
                                        onChange={(e) => setNewRow({ ...newRow, sku_abbrev_no_padding: e.target.value })}
                                        placeholder="C"
                                        inputProps={{ maxLength: 4 }}
                                    />
                                </TableCell>
                                <TableCell>
                                    <TextField
                                        size="small"
                                        fullWidth
                                        value={newRow.sku_abbrev_with_padding || ''}
                                        onChange={(e) => setNewRow({ ...newRow, sku_abbrev_with_padding: e.target.value })}
                                        placeholder="CG"
                                        inputProps={{ maxLength: 4 }}
                                    />
                                </TableCell>
                                <TableCell align="center">
                                    <Checkbox
                                        checked={newRow.ebay_variation_enabled || false}
                                        onChange={(e) => setNewRow({ ...newRow, ebay_variation_enabled: e.target.checked })}
                                    />
                                </TableCell>
                                <TableCell>
                                    <TextField
                                        size="small"
                                        type="number"
                                        fullWidth
                                        value={newRow.sort_order ?? 0}
                                        onChange={(e) => setNewRow({ ...newRow, sort_order: parseInt(e.target.value) || 0 })}
                                        inputProps={{ min: 0 }}
                                    />
                                </TableCell>
                                <TableCell align="right">
                                    <IconButton onClick={handleSaveNew} size="small" color="primary">
                                        <SaveIcon />
                                    </IconButton>
                                    <IconButton onClick={handleCancelNew} size="small" color="error">
                                        <DeleteIcon />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        )}

                        {/* Existing Rows */}
                        {configs.map((config) => (
                            <TableRow key={config.id}>
                                <TableCell>
                                    <Typography
                                        variant="body2"
                                        fontWeight="medium"
                                        sx={{ whiteSpace: 'nowrap' }}
                                    >
                                        {formatMaterialRoleLabel(config.role, config.display_name)}
                                    </Typography>
                                </TableCell>
                                <TableCell>
                                    <TextField
                                        size="small"
                                        fullWidth
                                        defaultValue={config.display_name || ''}
                                        onBlur={(e) => handleUpdateField(config.id, 'display_name', e.target.value)}
                                    />
                                </TableCell>
                                <TableCell>
                                    <TextField
                                        size="small"
                                        fullWidth
                                        defaultValue={config.display_name_with_padding || ''}
                                        onBlur={(e) => handleUpdateField(config.id, 'display_name_with_padding', e.target.value)}
                                    />
                                </TableCell>
                                <TableCell>
                                    <TextField
                                        size="small"
                                        fullWidth
                                        defaultValue={config.sku_abbrev_no_padding || ''}
                                        onBlur={(e) => handleUpdateField(config.id, 'sku_abbrev_no_padding', e.target.value)}
                                        inputProps={{ maxLength: 4 }}
                                    />
                                </TableCell>
                                <TableCell>
                                    <TextField
                                        size="small"
                                        fullWidth
                                        defaultValue={config.sku_abbrev_with_padding || ''}
                                        onBlur={(e) => handleUpdateField(config.id, 'sku_abbrev_with_padding', e.target.value)}
                                        inputProps={{ maxLength: 4 }}
                                    />
                                </TableCell>
                                <TableCell align="center">
                                    <Checkbox
                                        checked={config.ebay_variation_enabled}
                                        onChange={(e) => handleUpdateField(config.id, 'ebay_variation_enabled', e.target.checked)}
                                    />
                                </TableCell>
                                <TableCell>
                                    <TextField
                                        size="small"
                                        type="number"
                                        fullWidth
                                        defaultValue={config.sort_order}
                                        onBlur={(e) => handleUpdateField(config.id, 'sort_order', e.target.value)}
                                        inputProps={{ min: 0 }}
                                    />
                                </TableCell>
                                <TableCell align="right">
                                    <IconButton onClick={() => handleDelete(config.id)} size="small" color="error">
                                        <DeleteIcon />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        ))}

                        {configs.length === 0 && !newRow && (
                            <TableRow>
                                <TableCell colSpan={8} align="center">
                                    No material role configs found. Click "New Role Config" to add one.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
        </Box>
    )
}
