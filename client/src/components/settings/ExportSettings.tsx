
import React, { useState, useEffect } from 'react';
import { Box, Typography, TextField, Button, Alert, Paper, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { settingsApi } from '../../services/api';
import { ExportSetting } from '../../types';

export const ExportSettings: React.FC = () => {
    const [setting, setSetting] = useState<ExportSetting | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            setLoading(true);
            const data = await settingsApi.getExport();
            setSetting(data);
        } catch (err) {
            console.error(err);
            setError('Failed to load export settings');
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!setting) return;
        try {
            setSaving(true);
            setError(null);
            setSuccess(null);
            const normalizePattern = (value?: string | null): string | null => {
                if (value == null) return null;
                return value.trim() === '' ? null : value;
            };
            const payload = {
                ...setting,
                ebay_parent_image_pattern: normalizePattern(setting.ebay_parent_image_pattern),
                ebay_variation_image_pattern: normalizePattern(setting.ebay_variation_image_pattern),
            };
            const updated = await settingsApi.updateExport(payload);
            setSetting(updated);
            setSuccess('Export settings saved successfully');
        } catch (err) {
            console.error(err);
            setError('Failed to save export settings');
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <Typography>Loading...</Typography>;

    const descriptionSelectionMode = setting?.ebay_description_selection_mode || 'GLOBAL_PRIMARY';
    const descriptionModeHelpText =
        descriptionSelectionMode === 'EQUIPMENT_TYPE_PRIMARY'
            ? 'Type-specific descriptions are used when assigned; otherwise Global is used.'
            : 'Global description is used for all equipment types unless Global is blank; then type-specific descriptions are used.';

    return (
        <Box sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Export Configuration</Typography>

            {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
            {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>{success}</Alert>}

            <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom>Default Save Path Template</Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                    Define the default folder structure for generated Amazon export files.
                    You can use placeholders like <code>[Manufacturer_Name]</code>, <code>[Series_Name]</code>, and <code>[Marketplace]</code>.
                </Typography>
                <Typography variant="caption" display="block" sx={{ mb: 1, fontFamily: 'monospace', bgcolor: '#f5f5f5', p: 1 }}>
                    Example: C:\MyFiles\Exports\[Manufacturer_Name]\[Series_Name]
                </Typography>

                <TextField
                    fullWidth
                    label="Path Template"
                    value={setting?.default_save_path_template || ''}
                    onChange={(e) => setSetting(prev => prev ? { ...prev, default_save_path_template: e.target.value } : null)}
                    helperText="Note: Actual file saving to this path requires browser permission or manual selection."
                    sx={{ mb: 2 }}
                />

                <TextField
                    fullWidth
                    multiline
                    minRows={3}
                    label="eBay Parent Image Pattern"
                    value={setting?.ebay_parent_image_pattern || ''}
                    onChange={(e) => setSetting(prev => prev ? { ...prev, ebay_parent_image_pattern: e.target.value } : null)}
                    helperText="Must include [INDEX] or [IMAGE_INDEX]. Supports [Model_Name], [Series_Name], [Manufacturer_Name]."
                    sx={{ mb: 2 }}
                />

                <TextField
                    fullWidth
                    multiline
                    minRows={3}
                    label="eBay Variation Image Pattern"
                    value={setting?.ebay_variation_image_pattern || ''}
                    onChange={(e) => setSetting(prev => prev ? { ...prev, ebay_variation_image_pattern: e.target.value } : null)}
                    helperText="Must include [COLOR_ABBR] (or legacy [COLOR_SKU]) and [INDEX]/[IMAGE_INDEX]."
                    sx={{ mb: 2 }}
                />

                <FormControl fullWidth sx={{ mb: 1.5 }}>
                    <InputLabel id="description-selection-mode-label">Description selection mode</InputLabel>
                    <Select
                        labelId="description-selection-mode-label"
                        label="Description selection mode"
                        value={descriptionSelectionMode}
                        onChange={(e) =>
                            setSetting(prev => prev ? {
                                ...prev,
                                ebay_description_selection_mode: e.target.value as 'GLOBAL_PRIMARY' | 'EQUIPMENT_TYPE_PRIMARY'
                            } : null)
                        }
                    >
                        <MenuItem value="GLOBAL_PRIMARY">Global primary (use Global description unless missing)</MenuItem>
                        <MenuItem value="EQUIPMENT_TYPE_PRIMARY">Equipment-type primary (use specific equipment-type description unless missing)</MenuItem>
                    </Select>
                </FormControl>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {descriptionModeHelpText}
                </Typography>

                <Button
                    variant="contained"
                    onClick={handleSave}
                    disabled={saving}
                >
                    {saving ? 'Saving...' : 'Save Configuration'}
                </Button>
            </Paper>
        </Box>
    );
};
