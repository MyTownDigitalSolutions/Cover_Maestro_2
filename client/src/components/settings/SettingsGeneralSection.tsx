import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, Grid, Snackbar, TextField, Typography } from '@mui/material';
import { settingsApi } from '../../services/api';
import { LaborSetting, MarketplaceFeeRate, VariantProfitSetting } from '../../types';

interface SettingsGeneralSectionProps {
    showLabor?: boolean;
    showFees?: boolean;
    showProfits?: boolean;
}

export const SettingsGeneralSection: React.FC<SettingsGeneralSectionProps> = ({
    showLabor = false,
    showFees = false,
    showProfits = false,
}) => {
    const [labor, setLabor] = useState<LaborSetting | null>(null);
    const [fees, setFees] = useState<MarketplaceFeeRate[]>([]);
    const [profits, setProfits] = useState<VariantProfitSetting[]>([]);
    const [feesAvailable, setFeesAvailable] = useState(true);

    const [hourlyRateDollars, setHourlyRateDollars] = useState<string>('');
    const [localFees, setLocalFees] = useState<Record<string, string>>({});
    const [feeErrors, setFeeErrors] = useState<Record<string, string>>({});
    const [profitInputs, setProfitInputs] = useState<Record<string, string>>({});
    const [snackbar, setSnackbar] = useState<{ message: string; severity: 'success' | 'error' } | null>(null);

    const centsToDollars = (cents: number) => (cents / 100).toFixed(2);
    const dollarsToCents = (dollars: string) => {
        const num = Number(dollars);
        if (!Number.isFinite(num)) return 0;
        return Math.round(num * 100);
    };

    const fetchData = async () => {
        const [l, f, p] = await Promise.allSettled([
            settingsApi.getLabor(),
            settingsApi.listFees(),
            settingsApi.listProfits()
        ]);

        if (l.status === 'fulfilled') {
            setLabor(l.value);
            setHourlyRateDollars(centsToDollars(l.value.hourly_rate_cents));
        }

        if (p.status === 'fulfilled') {
            setProfits(p.value);
            const next: Record<string, string> = {};
            p.value.forEach((profit) => {
                next[profit.variant_key] = centsToDollars(profit.profit_cents);
            });
            setProfitInputs(next);
        }

        if (f.status === 'fulfilled') {
            setFeesAvailable(true);
            setFees(f.value);
            const nextFees: Record<string, string> = {};
            f.value.forEach((fee) => {
                nextFees[fee.marketplace] = typeof fee.fee_rate === 'number' ? (fee.fee_rate * 100).toFixed(2) : '';
            });
            if (f.value.length === 0) {
                ['amazon', 'ebay', 'etsy', 'reverb'].forEach((marketplace) => {
                    nextFees[marketplace] = '0.00';
                });
            }
            setLocalFees(nextFees);
            setFeeErrors({});
        } else {
            const status = (f as PromiseRejectedResult)?.reason?.response?.status;
            if (status === 404) {
                setFeesAvailable(false);
                setFees([]);
                setLocalFees({
                    amazon: '0.00',
                    ebay: '0.00',
                    etsy: '0.00',
                    reverb: '0.00',
                });
            }
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleLaborSave = async () => {
        if (!labor) return;
        try {
            await settingsApi.updateLabor({
                ...labor,
                hourly_rate_cents: dollarsToCents(hourlyRateDollars),
            });
            await fetchData();
            setSnackbar({ message: 'Labor settings saved', severity: 'success' });
        } catch {
            setSnackbar({ message: 'Error saving labor settings', severity: 'error' });
        }
    };

    const handleProfitSave = async (setting: VariantProfitSetting, newCents: number) => {
        try {
            await settingsApi.updateProfit({ ...setting, profit_cents: newCents });
            await fetchData();
            setSnackbar({ message: 'Variant profit saved', severity: 'success' });
        } catch {
            setSnackbar({ message: 'Error saving variant profit', severity: 'error' });
        }
    };

    const validateFee = (value: string) => {
        if (value.trim() === '') return 'Required';
        if (!/^\d+(\.\d{0,2})?$/.test(value)) return 'Up to 2 decimals';
        const num = Number(value);
        if (Number.isNaN(num) || num < 0 || num > 100) return '0-100 only';
        return '';
    };

    const handleFeeChange = (marketplace: string, value: string) => {
        setLocalFees((prev) => ({ ...prev, [marketplace]: value }));
        setFeeErrors((prev) => ({ ...prev, [marketplace]: validateFee(value) }));
    };

    const handleFeeSaveAll = async () => {
        if (!feesAvailable) {
            setSnackbar({ message: 'Fee rate API not available', severity: 'error' });
            return;
        }
        const nextErrors: Record<string, string> = {};
        const feeTargets = fees.length > 0 ? fees.map((f) => f.marketplace) : ['amazon', 'ebay', 'etsy', 'reverb'];
        feeTargets.forEach((marketplace) => {
            const val = localFees[marketplace] ?? '';
            const err = validateFee(val);
            if (err) nextErrors[marketplace] = err;
        });

        setFeeErrors(nextErrors);
        if (Object.keys(nextErrors).length > 0) {
            setSnackbar({ message: 'Fix fee rate errors before saving', severity: 'error' });
            return;
        }

        try {
            const targets = feeTargets.map((marketplace) => ({
                marketplace,
                fee_rate: Number(localFees[marketplace] ?? '0') / 100,
            }));
            await Promise.all(targets.map((fee) => settingsApi.updateFee(fee)));
            await fetchData();
            setSnackbar({ message: 'Fee rates saved', severity: 'success' });
        } catch {
            setSnackbar({ message: 'Error saving fee rates', severity: 'error' });
        }
    };

    return (
        <Box sx={{ p: 2 }}>
            {showLabor && labor && (
                <>
                    <Typography variant="h6" gutterBottom>Labor Settings</Typography>
                    <Grid container spacing={2} sx={{ mb: 4 }}>
                        <Grid item xs={12} md={4}>
                            <TextField
                                label="Hourly Rate ($)"
                                type="number"
                                inputProps={{ step: '0.01', min: 0 }}
                                fullWidth
                                value={hourlyRateDollars}
                                onChange={(e) => setHourlyRateDollars(e.target.value)}
                            />
                        </Grid>
                        <Grid item xs={12} md={4}>
                            <TextField
                                label="Mins (No Padding)"
                                type="number"
                                fullWidth
                                value={labor.minutes_no_padding}
                                onChange={(e) => setLabor({ ...labor, minutes_no_padding: parseInt(e.target.value || '0', 10) })}
                            />
                        </Grid>
                        <Grid item xs={12} md={4}>
                            <TextField
                                label="Mins (With Padding)"
                                type="number"
                                fullWidth
                                value={labor.minutes_with_padding}
                                onChange={(e) => setLabor({ ...labor, minutes_with_padding: parseInt(e.target.value || '0', 10) })}
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <Button variant="contained" onClick={handleLaborSave}>Save Labor Settings</Button>
                        </Grid>
                    </Grid>
                </>
            )}

            {showFees && (
                <>
                    <Typography variant="h6" gutterBottom>Marketplace Fee Rates</Typography>
                    <Grid container spacing={2} sx={{ mb: 2 }}>
                        {!feesAvailable && (
                            <Grid item xs={12}>
                                <Alert severity="warning">Fee rate API not available</Alert>
                            </Grid>
                        )}
                        {(fees.length > 0 ? fees : ['amazon', 'ebay', 'etsy', 'reverb'].map((marketplace) => ({ marketplace, fee_rate: 0 } as MarketplaceFeeRate))).map((fee) => (
                            <Grid item xs={12} sm={6} md={3} key={fee.marketplace}>
                                <TextField
                                    label={fee.marketplace}
                                    type="number"
                                    inputProps={{ step: '0.01', min: 0, max: 100 }}
                                    fullWidth
                                    value={localFees[fee.marketplace] ?? ''}
                                    onChange={(e) => handleFeeChange(fee.marketplace, e.target.value)}
                                    error={Boolean(feeErrors[fee.marketplace])}
                                    helperText={feeErrors[fee.marketplace] || 'Percent (0-100)'}
                                />
                            </Grid>
                        ))}
                        <Grid item xs={12}>
                            <Button variant="contained" onClick={handleFeeSaveAll} disabled={!feesAvailable}>
                                Save Fee Rates
                            </Button>
                        </Grid>
                    </Grid>
                </>
            )}

            {showProfits && (
                <>
                    <Typography variant="h6" gutterBottom>Variant Profits ($)</Typography>
                    <Grid container spacing={2}>
                        {profits.map((profit) => (
                            <Grid item xs={12} sm={6} md={3} key={profit.variant_key}>
                                <TextField
                                    label={profit.variant_key.replace(/_/g, ' ')}
                                    type="number"
                                    inputProps={{ step: '0.01', min: 0 }}
                                    fullWidth
                                    value={profitInputs[profit.variant_key] ?? ''}
                                    onChange={(e) => setProfitInputs((prev) => ({ ...prev, [profit.variant_key]: e.target.value }))}
                                    onBlur={(e) => handleProfitSave(profit, dollarsToCents(e.target.value))}
                                />
                            </Grid>
                        ))}
                    </Grid>
                </>
            )}

            <Snackbar open={Boolean(snackbar)} autoHideDuration={4000} onClose={() => setSnackbar(null)}>
                {snackbar ? (
                    <Alert onClose={() => setSnackbar(null)} severity={snackbar.severity} sx={{ width: '100%' }}>
                        {snackbar.message}
                    </Alert>
                ) : (
                    <div />
                )}
            </Snackbar>
        </Box>
    );
};

