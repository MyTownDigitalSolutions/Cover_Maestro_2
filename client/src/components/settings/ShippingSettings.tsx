import React, { useState, useEffect } from 'react';
import {
    Box, Table, TableBody, TableCell, TableContainer,
    TableHead, TableRow, Paper, Button, FormControl, InputLabel,
    Select, MenuItem, TextField, Tabs, Tab, Grid, Typography
} from '@mui/material';
import { settingsApi, enumsApi } from '../../services/api';
import { ShippingRateCard, ShippingRateTier, MarketplaceShippingProfile, EnumValue, ShippingZoneRateNormalized, ShippingZone } from '../../types';

const centsToDollars = (cents: number | null | undefined) => (typeof cents === 'number' ? (cents / 100).toFixed(2) : '');
const dollarsToCents = (dollars: string) => {
    const n = Number(dollars);
    if (!Number.isFinite(n)) return 0;
    return Math.round(n * 100);
};

export const ShippingSettings: React.FC = () => {
    const [tab, setTab] = useState(0);

    return (
        <Box sx={{ p: 2 }}>
            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
                <Tab label="Rate Cards" />
                <Tab label="Tiers" />
                <Tab label="Zone Rates" />
                <Tab label="Marketplace Profiles" />
            </Tabs>
            {tab === 0 && <RateCardsTab />}
            {tab === 1 && <TiersTab />}
            {tab === 2 && <ZoneRatesTab />}
            {tab === 3 && <MarketplaceProfilesTab />}
        </Box>
    );
};

const RateCardsTab = () => {
    const [cards, setCards] = useState<ShippingRateCard[]>([]);
    const [newName, setNewName] = useState('');
    const [selectedCardId, setSelectedCardId] = useState<number | null>(null);
    const [zones, setZones] = useState<ShippingZone[]>([]);
    const [savingMatrix, setSavingMatrix] = useState(false);
    const [matrixRows, setMatrixRows] = useState<Array<{
        key: string;
        tierId: number | null;
        label: string;
        maxOz: string;
        rateByZone: Record<number, string>;
    }>>([]);

    const loadCards = async () => {
        const c = await settingsApi.listRateCards();
        setCards(c);
    };

    const loadMatrix = async (cardId: number) => {
        const tiers = (await settingsApi.listTiers(cardId)).sort((a, b) => a.max_oz - b.max_oz);
        const zoneRatesByTier = await Promise.all(
            tiers.map(async (tier) => {
                const rates = await settingsApi.listZoneRates(tier.id);
                return { tierId: tier.id, rates };
            })
        );

        const rows = tiers.map((tier) => {
            const tierRates = zoneRatesByTier.find((x) => x.tierId === tier.id)?.rates || [];
            const byZone: Record<number, string> = {};
            zones.forEach((z) => {
                const found = tierRates.find((r) => r.zone_id === z.id);
                byZone[z.id] = found && found.rate_cents != null ? centsToDollars(found.rate_cents) : '';
            });
            return {
                key: `tier-${tier.id}`,
                tierId: tier.id,
                label: tier.label || '',
                maxOz: String(tier.max_oz),
                rateByZone: byZone,
            };
        });

        setMatrixRows(rows);
    };

    useEffect(() => {
        const load = async () => {
            await loadCards();
            const z = await settingsApi.listZones();
            const ordered = z.filter((x) => x.active).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
            setZones(ordered);
        };
        load();
    }, []);

    useEffect(() => {
        if (selectedCardId && zones.length > 0) {
            loadMatrix(selectedCardId);
        } else if (!selectedCardId) {
            setMatrixRows([]);
        }
    }, [selectedCardId, zones]);

    const createCard = async () => {
        if (!newName.trim()) return;
        await settingsApi.createRateCard({ name: newName.trim() });
        setNewName('');
        loadCards();
    };

    const removeCard = async (id: number) => {
        await settingsApi.deleteRateCard(id);
        if (selectedCardId === id) {
            setSelectedCardId(null);
        }
        loadCards();
    };

    const addMatrixRow = () => {
        const byZone: Record<number, string> = {};
        zones.forEach((z) => { byZone[z.id] = ''; });
        setMatrixRows((prev) => ([
            ...prev,
            {
                key: `new-${Date.now()}-${Math.random()}`,
                tierId: null,
                label: '',
                maxOz: '',
                rateByZone: byZone,
            }
        ]));
    };

    const removeMatrixRow = async (rowKey: string) => {
        const row = matrixRows.find((r) => r.key === rowKey);
        if (!row) return;
        if (row.tierId) {
            await settingsApi.deleteTier(row.tierId);
        }
        setMatrixRows((prev) => prev.filter((r) => r.key !== rowKey));
    };

    const updateRowField = (rowKey: string, field: 'label' | 'maxOz', value: string) => {
        setMatrixRows((prev) => prev.map((r) => r.key === rowKey ? { ...r, [field]: value } : r));
    };

    const updateRateCell = (rowKey: string, zoneId: number, value: string) => {
        setMatrixRows((prev) =>
            prev.map((r) => r.key === rowKey
                ? { ...r, rateByZone: { ...r.rateByZone, [zoneId]: value } }
                : r
            )
        );
    };

    const saveMatrix = async () => {
        if (!selectedCardId) return;
        setSavingMatrix(true);
        try {
            const sortedRows = [...matrixRows].sort((a, b) => {
                const aNum = Number(a.maxOz || 0);
                const bNum = Number(b.maxOz || 0);
                return aNum - bNum;
            });

            for (const row of sortedRows) {
                const maxOz = Number(row.maxOz);
                if (!Number.isFinite(maxOz) || maxOz <= 0) {
                    continue;
                }

                let tierId = row.tierId;
                if (tierId) {
                    await settingsApi.updateTier(tierId, { label: row.label || undefined, max_weight_oz: maxOz });
                } else {
                    const created = await settingsApi.createTier(selectedCardId, { label: row.label || undefined, max_weight_oz: maxOz });
                    tierId = created.id;
                }

                for (const zoneObj of zones) {
                    const raw = (row.rateByZone[zoneObj.id] ?? '').trim();
                    const cents = raw === '' ? null : dollarsToCents(raw);
                    await settingsApi.upsertTierZoneRate(tierId, zoneObj.id, cents);
                }
            }

            await loadMatrix(selectedCardId);
        } finally {
            setSavingMatrix(false);
        }
    };

    return (
        <Box>
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <TextField label="Name" size="small" value={newName} onChange={e => setNewName(e.target.value)} />
                <Button variant="contained" onClick={createCard}>Add Card</Button>
            </Box>
            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>ID</TableCell>
                            <TableCell>Name</TableCell>
                            <TableCell>Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {cards.map(c => (
                            <TableRow
                                key={c.id}
                                hover
                                selected={selectedCardId === c.id}
                                onClick={() => setSelectedCardId(c.id)}
                                sx={{ cursor: 'pointer' }}
                            >
                                <TableCell>{c.id}</TableCell>
                                <TableCell>{c.name}</TableCell>
                                <TableCell>
                                    <Button size="small" color="error" onClick={(e) => { e.stopPropagation(); removeCard(c.id); }}>Delete</Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            {selectedCardId && (
                <Paper sx={{ mt: 2, p: 2 }}>
                    <Typography variant="subtitle1" sx={{ mb: 2 }}>Card Details: {cards.find(c => c.id === selectedCardId)?.name}</Typography>
                    <Grid container spacing={2} sx={{ mb: 2 }}>
                        <Grid item xs={4}>
                            <Button fullWidth variant="outlined" onClick={addMatrixRow}>Add Row</Button>
                        </Grid>
                        <Grid item xs={4}>
                            <Button fullWidth variant="contained" onClick={saveMatrix} disabled={savingMatrix}>
                                {savingMatrix ? 'Saving...' : 'Save Matrix'}
                            </Button>
                        </Grid>
                    </Grid>

                    <TableContainer component={Paper} sx={{ mb: 2 }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Tier Label</TableCell>
                                    <TableCell>Weight Not Over (oz)</TableCell>
                                    {zones.map((z) => (
                                        <TableCell key={`zone-head-${z.id}`}>Zone {z.code}</TableCell>
                                    ))}
                                    <TableCell>Actions</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {matrixRows.map((row) => (
                                    <TableRow key={row.key}>
                                        <TableCell>
                                            <TextField
                                                fullWidth
                                                size="small"
                                                value={row.label}
                                                onChange={(e) => updateRowField(row.key, 'label', e.target.value)}
                                                placeholder="e.g. <8 oz"
                                                sx={{ minWidth: 140 }}
                                                inputProps={{ maxLength: 24 }}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <TextField
                                                fullWidth
                                                size="small"
                                                type="number"
                                                value={row.maxOz}
                                                onChange={(e) => updateRowField(row.key, 'maxOz', e.target.value)}
                                                sx={{ minWidth: 90 }}
                                                inputProps={{ step: '0.001', min: 0, style: { fontSize: 24 } }}
                                            />
                                        </TableCell>
                                        {zones.map((z) => (
                                            <TableCell key={`${row.key}-zone-${z.id}`}>
                                                <TextField
                                                    size="small"
                                                    fullWidth
                                                    type="number"
                                                    inputProps={{ step: '0.01', min: 0, style: { fontSize: 24 } }}
                                                    value={row.rateByZone[z.id] ?? ''}
                                                    onChange={(e) => updateRateCell(row.key, z.id, e.target.value)}
                                                    placeholder="0.00"
                                                    sx={{ minWidth: 140 }}
                                                />
                                            </TableCell>
                                        ))}
                                        <TableCell>
                                            <Button size="small" color="error" onClick={() => removeMatrixRow(row.key)}>Delete</Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Paper>
            )}
        </Box>
    );
};

const TiersTab = () => {
    const [cards, setCards] = useState<ShippingRateCard[]>([]);
    const [selectedCard, setSelectedCard] = useState<number | ''>('');
    const [tiers, setTiers] = useState<ShippingRateTier[]>([]);
    const [max, setMax] = useState('');

    useEffect(() => { settingsApi.listRateCards().then(setCards); }, []);
    useEffect(() => {
        if (selectedCard) settingsApi.listTiers(Number(selectedCard)).then(setTiers);
        else setTiers([]);
    }, [selectedCard]);

    const create = async () => {
        if (!selectedCard || !max) return;
        await settingsApi.createTier(Number(selectedCard), { max_weight_oz: parseFloat(max) });
        settingsApi.listTiers(Number(selectedCard)).then(setTiers);
    };

    return (
        <Box>
            <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Select Rate Card</InputLabel>
                <Select value={selectedCard} label="Select Rate Card" onChange={e => setSelectedCard(e.target.value as number)}>
                    {cards.map(c => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
                </Select>
            </FormControl>
            {selectedCard && (
                <Box>
                    <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                        <TextField label="Max oz" size="small" type="number" value={max} onChange={e => setMax(e.target.value)} />
                        <Button variant="contained" onClick={create}>Add Tier</Button>
                    </Box>
                    <TableContainer component={Paper}>
                        <Table size="small">
                            <TableHead><TableRow><TableCell>ID</TableCell><TableCell>Min Oz</TableCell><TableCell>Max Oz</TableCell></TableRow></TableHead>
                            <TableBody>
                                {tiers.map(t => <TableRow key={t.id}><TableCell>{t.id}</TableCell><TableCell>{t.min_oz}</TableCell><TableCell>{t.max_oz}</TableCell></TableRow>)}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Box>
            )}
        </Box>
    );
};

const ZoneRatesTab = () => {
    const [cards, setCards] = useState<ShippingRateCard[]>([]);
    const [tiers, setTiers] = useState<ShippingRateTier[]>([]);
    const [selectedCard, setSelectedCard] = useState<number | ''>('');
    const [selectedTier, setSelectedTier] = useState<number | ''>('');
    const [rates, setRates] = useState<ShippingZoneRateNormalized[]>([]);
    const [zone, setZone] = useState('');
    const [rateDollars, setRateDollars] = useState('');

    useEffect(() => { settingsApi.listRateCards().then(setCards); }, []);
    useEffect(() => { if (selectedCard) settingsApi.listTiers(Number(selectedCard)).then(setTiers); }, [selectedCard]);
    useEffect(() => { if (selectedTier) settingsApi.listZoneRates(Number(selectedTier)).then(setRates); }, [selectedTier]);

    const saveRate = async () => {
        if (!selectedCard || !selectedTier || !zone || !rateDollars) return;
        await settingsApi.createZoneRate({
            rate_card_id: Number(selectedCard),
            tier_id: Number(selectedTier),
            zone: parseInt(zone, 10),
            rate_cents: dollarsToCents(rateDollars)
        });
        settingsApi.listZoneRates(Number(selectedTier)).then(setRates);
        setZone('');
        setRateDollars('');
    };

    return (
        <Box>
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <FormControl sx={{ minWidth: 200 }}>
                    <InputLabel>Card</InputLabel>
                    <Select value={selectedCard} label="Card" onChange={e => setSelectedCard(e.target.value as number)}>
                        {cards.map(c => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
                    </Select>
                </FormControl>
                <FormControl sx={{ minWidth: 200 }}>
                    <InputLabel>Tier</InputLabel>
                    <Select value={selectedTier} label="Tier" onChange={e => setSelectedTier(e.target.value as number)}>
                        {tiers.map(t => <MenuItem key={t.id} value={t.id}>{t.min_oz} - {t.max_oz} oz</MenuItem>)}
                    </Select>
                </FormControl>
            </Box>

            {selectedTier && (
                <Box>
                    <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                        <TextField label="Zone" size="small" type="number" value={zone} onChange={e => setZone(e.target.value)} />
                        <TextField
                            label="Rate ($)"
                            size="small"
                            type="number"
                            inputProps={{ step: '0.01', min: 0 }}
                            value={rateDollars}
                            onChange={e => setRateDollars(e.target.value)}
                        />
                        <Button variant="contained" onClick={saveRate}>Set Rate</Button>
                    </Box>
                    <TableContainer component={Paper}>
                        <Table size="small">
                            <TableHead><TableRow><TableCell>Zone</TableCell><TableCell>Rate ($)</TableCell></TableRow></TableHead>
                            <TableBody>
                                {rates.sort((a, b) => a.zone_id - b.zone_id).map(r => <TableRow key={r.zone_id}><TableCell>{r.zone_code}</TableCell><TableCell>{r.rate_cents == null ? '-' : centsToDollars(r.rate_cents)}</TableCell></TableRow>)}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Box>
            )}
        </Box>
    );
};

const MarketplaceProfilesTab = () => {
    const [profiles, setProfiles] = useState<MarketplaceShippingProfile[]>([]);
    const [marketplaces, setMarketplaces] = useState<EnumValue[]>([{ value: 'DEFAULT', name: 'Default' }]);
    const [cards, setCards] = useState<ShippingRateCard[]>([]);
    const [selectedMp, setSelectedMp] = useState('DEFAULT');
    const [selectedCard, setSelectedCard] = useState<number | ''>('');
    const [pricingZone, setPricingZone] = useState<number>(7);
    const [editingProfileId, setEditingProfileId] = useState<number | null>(null);

    const load = async () => {
        const [p, m, c] = await Promise.all([settingsApi.listProfiles(), enumsApi.marketplaces(), settingsApi.listRateCards()]);
        setProfiles(p);
        setMarketplaces([{ value: 'DEFAULT', name: 'Default' }, ...m]);
        setCards(c);
    };
    useEffect(() => { load(); }, []);

    const assign = async () => {
        if (!selectedCard) return;
        if (editingProfileId) {
            await settingsApi.updateProfile(editingProfileId, {
                marketplace: selectedMp,
                rate_card_id: Number(selectedCard),
                pricing_zone: pricingZone
            });
            setEditingProfileId(null);
        } else {
            await settingsApi.assignProfile({
                marketplace: selectedMp,
                rate_card_id: Number(selectedCard),
                pricing_zone: pricingZone
            });
        }
        load();
        alert('Profile saved');
    };

    const startEdit = (p: MarketplaceShippingProfile) => {
        setEditingProfileId(p.id);
        setSelectedMp(p.marketplace);
        setSelectedCard(p.rate_card_id);
        setPricingZone(p.pricing_zone);
    };

    const cancelEdit = () => {
        setEditingProfileId(null);
        setSelectedMp('DEFAULT');
        setSelectedCard('');
        setPricingZone(7);
    };

    const removeProfile = async (id: number) => {
        await settingsApi.deleteProfile(id);
        if (editingProfileId === id) cancelEdit();
        load();
    };

    return (
        <Box>
            <Paper sx={{ p: 2, mb: 2 }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid item xs={3}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Marketplace</InputLabel>
                            <Select value={selectedMp} label="Marketplace" onChange={e => setSelectedMp(e.target.value)}>
                                {marketplaces.map(m => <MenuItem key={m.value} value={m.value}>{m.name}</MenuItem>)}
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item xs={3}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Rate Card</InputLabel>
                            <Select value={selectedCard} label="Rate Card" onChange={e => setSelectedCard(e.target.value as number)}>
                                {cards.map(c => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item xs={3}>
                        <TextField
                            label="Pricing Zone"
                            size="small"
                            type="number"
                            fullWidth
                            value={pricingZone}
                            onChange={e => setPricingZone(parseInt(e.target.value, 10))}
                        />
                    </Grid>
                    <Grid item xs={3}>
                        <Button variant="contained" fullWidth onClick={assign}>
                            {editingProfileId ? 'Update Profile' : 'Assign Profile'}
                        </Button>
                        {editingProfileId && (
                            <Button sx={{ mt: 1 }} fullWidth onClick={cancelEdit}>Cancel Edit</Button>
                        )}
                    </Grid>
                </Grid>
            </Paper>

            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Marketplace</TableCell>
                            <TableCell>Card</TableCell>
                            <TableCell>Zone</TableCell>
                            <TableCell>Effective</TableCell>
                            <TableCell>Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {profiles.map(p => {
                            const cardName = cards.find(c => c.id === p.rate_card_id)?.name || p.rate_card_id;
                            return (
                                <TableRow key={p.id}>
                                    <TableCell>{p.marketplace}</TableCell>
                                    <TableCell>{cardName}</TableCell>
                                    <TableCell>{p.pricing_zone}</TableCell>
                                    <TableCell>{new Date(p.effective_date).toLocaleDateString()}</TableCell>
                                    <TableCell>
                                        <Button size="small" onClick={() => startEdit(p)}>Edit</Button>
                                        <Button size="small" color="error" onClick={() => removeProfile(p.id)}>Delete</Button>
                                    </TableCell>
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </TableContainer>
        </Box>
    );
};
