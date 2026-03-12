
import { useEffect, useState } from 'react'
import { Chip, Stack, Tooltip } from '@mui/material'
import LocalShippingIcon from '@mui/icons-material/LocalShipping'
import { settingsApi } from '../services/api'
import type { ShippingDefaultSettingResponse } from '../types'

type ShippingModeChipsProps = {
    shippingCents: number | null | undefined
    weightOz?: number | null
}

export default function ShippingModeChips({ shippingCents, weightOz }: ShippingModeChipsProps) {
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(false)
    const [defaults, setDefaults] = useState<ShippingDefaultSettingResponse | null>(null)
    const [fixedDetails, setFixedDetails] = useState<{
        cardName: string
        tierMaxOz: number
        zoneCode: string
    } | null>(null)

    useEffect(() => {
        let mounted = true

        const loadSettings = async () => {
            try {
                setLoading(true)
                const data = await settingsApi.getShippingDefaults()

                if (mounted) {
                    setDefaults(data)

                    if (data.shipping_mode === 'fixed_cell') {
                        // Parallel fetch for fixed cell details
                        await loadFixedDetails(data, mounted)
                    }
                }
            } catch (err) {
                console.error("Failed to load shipping defaults for chips", err)
                if (mounted) setError(true)
            } finally {
                if (mounted) setLoading(false)
            }
        }

        loadSettings()

        return () => { mounted = false }
    }, [])

    const loadFixedDetails = async (d: ShippingDefaultSettingResponse, mounted: boolean) => {
        // We do not strictly need to crash if these fail, just best effort.
        try {
            let cardName = "Unknown Card"
            let tierMaxOz = 0

            // 1. Fetch card name
            if (d.assumed_rate_card_id) {
                const cards = await settingsApi.listRateCards(true)
                const c = cards.find(r => r.id === d.assumed_rate_card_id)
                if (c) cardName = c.name
            }

            // 2. Fetch tier
            if (d.assumed_rate_card_id && d.assumed_tier_id) {
                const tiers = await settingsApi.listTiers(d.assumed_rate_card_id, true)
                const t = tiers.find(x => x.id === d.assumed_tier_id)
                if (t) tierMaxOz = t.max_oz
            }

            if (mounted) {
                setFixedDetails({
                    cardName,
                    tierMaxOz,
                    zoneCode: d.assumed_zone_code || "?"
                })
            }
        } catch (e) {
            console.error("Error loading fixed cell details", e)
        }
    }

    const formatMoney = (cents: number) => `$${(cents / 100).toFixed(2)}`

    // Render logic
    const costLabel = (shippingCents !== null && shippingCents !== undefined)
        ? formatMoney(shippingCents)
        : "—"

    // Base Chip
    const costChip = (
        <Chip
            label={costLabel}
            color="default"
            size="small"
            icon={<LocalShippingIcon />}
            variant="outlined"
        />
    )

    if (loading) {
        return (
            <Stack direction="row" spacing={1} alignItems="center">
                {costChip}
                {/* Could show a tiny spinner or just nothing while loading */}
            </Stack>
        )
    }

    if (error || !defaults) {
        return (
            <Stack direction="row" spacing={1} alignItems="center">
                <Tooltip title="Shipping settings failed to load">
                    <Chip label="Mode Unknown" color="warning" variant="outlined" size="small" />
                </Tooltip>
                {costChip}
            </Stack>
        )
    }

    const mode = defaults.shipping_mode

    return (
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
            {costChip}

            {/* A) Calculated */}
            {mode === 'calculated' && (
                <>
                    <Tooltip title={`Calculated (weight-based)${weightOz ? ` @ ${weightOz.toFixed(1)} oz` : ''}`}>
                        <Chip label="Calculated" color="primary" size="small" />
                    </Tooltip>
                    {/* Only show weight chip here if caller didn't provide it elsewhere, 
                       but the prompt implies we should label it as weight-based. */}
                    <Chip label="Weight-based" variant="outlined" size="small" />
                </>
            )}

            {/* B) Flat */}
            {mode === 'flat' && (
                <>
                    <Tooltip title="Flat (global override)">
                        <Chip label="Flat" color="secondary" size="small" />
                    </Tooltip>
                    <Chip
                        label={`${formatMoney(defaults.flat_shipping_cents)} Global`}
                        variant="outlined"
                        size="small"
                    />
                </>
            )}

            {/* C) Fixed Cell */}
            {mode === 'fixed_cell' && (
                <>
                    <Tooltip title="Fixed Cell (assumption)">
                        <Chip label="Fixed Cell" color="success" size="small" />
                    </Tooltip>

                    {fixedDetails ? (
                        <>
                            <Tooltip title={`Rate Card: ${fixedDetails.cardName}`}>
                                <Chip label={fixedDetails.cardName} variant="outlined" size="small" sx={{ maxWidth: 150 }} />
                            </Tooltip>
                            <Chip label={`Zone ${fixedDetails.zoneCode}`} variant="outlined" size="small" />
                            <Tooltip title={`Weight Not Over ≤ ${fixedDetails.tierMaxOz} oz`}>
                                <Chip label={`≤ ${fixedDetails.tierMaxOz} oz`} variant="outlined" size="small" />
                            </Tooltip>
                        </>
                    ) : (
                        <Tooltip title="Incomplete settings">
                            <Chip label="(Incomplete)" size="small" variant="outlined" color="warning" />
                        </Tooltip>
                    )}
                </>
            )}
        </Stack>
    )
}
