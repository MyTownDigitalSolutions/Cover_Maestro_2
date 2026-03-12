import { useState } from 'react'
import {
    Box, Typography, Paper, Container, TextField, Button, Switch,
    FormControlLabel, Alert, CircularProgress, IconButton, InputAdornment,
    Divider, Card, CardContent, CardHeader, Chip, Checkbox, Table, TableBody,
    TableCell, TableHead, TableRow, TableContainer
} from '@mui/material'
import StorefrontIcon from '@mui/icons-material/Storefront'
import RefreshIcon from '@mui/icons-material/Refresh'
import SaveIcon from '@mui/icons-material/Save'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import VisibilityIcon from '@mui/icons-material/Visibility'
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorIcon from '@mui/icons-material/Error'
import DownloadIcon from '@mui/icons-material/Download'

// Masked token placeholder returned by backend when reveal is disabled
const MASKED_TOKEN = '********'

interface ReverbCredentials {
    marketplace: string
    is_enabled: boolean
    api_token: string
    base_url: string
    updated_at: string
}

interface TestResult {
    ok: boolean
    marketplace: string
    status_code: number
    account?: {
        shop_name?: string
        username?: string
        email?: string
        locale?: string
    }
    error?: string
}

interface OrderPreview {
    external_order_id: string
    external_order_number?: string
    order_date: string
    status_raw: string
    currency_code: string
    order_total_cents: number
    line_count: number
    address_count: number
}

interface ImportResult {
    import_run_id?: number
    dry_run: boolean
    total_fetched: number
    total_created: number
    total_updated: number
    total_failed: number
    failed_order_ids: string[]
    preview_orders?: OrderPreview[]
    // Debug fields
    filter_since_utc?: string
    filter_mode?: string
    timestamp_field_used?: string
    raw_fetched?: number
    filtered?: number
    pages_fetched?: number
    early_stop?: boolean
    undated_count?: number
    customers_matched?: number
    customers_created?: number
    orders_linked_to_customers?: number
    orders_missing_buyer_identity?: number
    debug_samples?: any[]
}

type StatusType = 'idle' | 'loading' | 'success' | 'error' | 'not_configured'

interface Status {
    type: StatusType
    message: string
}

/**
 * MarketplaceCredentialsPage - Manage API credentials for connected marketplaces
 */
export default function MarketplaceCredentialsPage() {
    // Admin key (required for all API calls)
    const [adminKey, setAdminKey] = useState('')

    // Reverb form state
    const [isEnabled, setIsEnabled] = useState(true)
    const [baseUrl, setBaseUrl] = useState('https://api.reverb.com')
    const [apiToken, setApiToken] = useState('')
    const [showToken, setShowToken] = useState(false)

    // Track if token was loaded from server (for masked token handling)
    const [loadedToken, setLoadedToken] = useState('')

    // Status indicators
    const [refreshStatus, setRefreshStatus] = useState<Status>({ type: 'idle', message: '' })
    const [saveStatus, setSaveStatus] = useState<Status>({ type: 'idle', message: '' })
    const [testStatus, setTestStatus] = useState<Status>({ type: 'idle', message: '' })
    const [testResult, setTestResult] = useState<TestResult | null>(null)

    // Loading states
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [isTesting, setIsTesting] = useState(false)

    // Reverb Orders Import state
    const [daysBack, setDaysBack] = useState(30)
    const [sinceIso, setSinceIso] = useState('')
    const [limit, setLimit] = useState(50)
    const [dryRun, setDryRun] = useState(true)
    const [debug, setDebug] = useState(false)
    const [importStatus, setImportStatus] = useState<Status>({ type: 'idle', message: '' })
    const [isImporting, setIsImporting] = useState(false)
    const [importResult, setImportResult] = useState<ImportResult | null>(null)

    // Reverb Orders Enrich state
    const [enrichDaysBack, setEnrichDaysBack] = useState(30)
    const [enrichSinceIso, setEnrichSinceIso] = useState('')
    const [enrichLimit, setEnrichLimit] = useState(50)
    const [enrichDryRun, setEnrichDryRun] = useState(true)
    const [enrichDebug, setEnrichDebug] = useState(false)
    const [enrichForce, setEnrichForce] = useState(false)
    const [enrichStatus, setEnrichStatus] = useState<Status>({ type: 'idle', message: '' })
    const [isEnriching, setIsEnriching] = useState(false)
    const [enrichResult, setEnrichResult] = useState<{
        dry_run: boolean
        orders_scanned: number
        orders_enriched: number
        orders_skipped: number
        lines_upserted: number
        addresses_upserted: number
        shipments_upserted: number
        failed_order_ids?: Record<string, string>
        preview_orders?: Array<{
            external_order_id: string
            order_id: number
            buyer_email?: string
            order_total_cents?: number
            shipping?: { name?: string; city?: string; postal_code?: string; country_code?: string }
            lines?: Array<{ title?: string; quantity?: number; line_total_cents?: number }>
            shipments?: Array<{ carrier?: string; tracking_number?: string }>
        }>
        debug?: Record<string, unknown>
    } | null>(null)

    const hasAdminKey = adminKey.trim().length > 0

    // Helper to make authenticated requests
    const authFetch = async (url: string, options: RequestInit = {}) => {
        const headers = {
            ...options.headers,
            'X-Admin-Key': adminKey,
        } as Record<string, string>

        if (options.method === 'PUT' || options.method === 'POST') {
            headers['Content-Type'] = 'application/json'
        }

        return fetch(url, { ...options, headers })
    }

    // Refresh credentials from server
    const handleRefresh = async () => {
        if (!hasAdminKey) return

        setIsRefreshing(true)
        setRefreshStatus({ type: 'loading', message: 'Loading credentials...' })
        setTestResult(null)

        try {
            const response = await authFetch('/api/marketplace-credentials/reverb')

            if (response.status === 404) {
                setRefreshStatus({ type: 'not_configured', message: 'Not configured yet. Save credentials to configure.' })
                setIsEnabled(true)
                setBaseUrl('https://api.reverb.com')
                setApiToken('')
                setLoadedToken('')
                return
            }

            if (response.status === 401) {
                setRefreshStatus({ type: 'error', message: 'Invalid Admin Key' })
                return
            }

            if (!response.ok) {
                const text = await response.text()
                setRefreshStatus({ type: 'error', message: `Error ${response.status}: ${text.slice(0, 100)}` })
                return
            }

            const data: ReverbCredentials = await response.json()
            setIsEnabled(data.is_enabled)
            setBaseUrl(data.base_url || 'https://api.reverb.com')
            setApiToken(data.api_token)
            setLoadedToken(data.api_token)
            setRefreshStatus({ type: 'success', message: `Loaded. Last updated: ${new Date(data.updated_at).toLocaleString()}` })
        } catch (err) {
            setRefreshStatus({ type: 'error', message: `Connection error: ${err instanceof Error ? err.message : 'Unknown'}` })
        } finally {
            setIsRefreshing(false)
        }
    }

    // Save credentials to server
    const handleSave = async () => {
        if (!hasAdminKey) return

        setIsSaving(true)
        setSaveStatus({ type: 'loading', message: 'Saving...' })

        try {
            // Determine if we should send the token
            // If token equals the masked placeholder and hasn't been edited, don't send it
            const tokenToSend = apiToken === MASKED_TOKEN && apiToken === loadedToken
                ? null  // Don't overwrite with masked token
                : apiToken

            // Build request body
            const body: Record<string, unknown> = {
                is_enabled: isEnabled,
                base_url: baseUrl,
            }

            // Only include api_token if we have a real value
            if (tokenToSend !== null) {
                body.api_token = tokenToSend
            }

            // If no token provided and this is first save, require it
            if (!tokenToSend && loadedToken === '') {
                setSaveStatus({ type: 'error', message: 'API Token is required for initial setup' })
                return
            }

            // For update with masked token unchanged, still need to send api_token (backend requires it)
            // The backend schema requires api_token, so we must send the masked value if unchanged
            if (tokenToSend === null) {
                body.api_token = apiToken
            }

            const response = await authFetch('/api/marketplace-credentials/reverb', {
                method: 'PUT',
                body: JSON.stringify(body),
            })

            if (response.status === 401) {
                setSaveStatus({ type: 'error', message: 'Invalid Admin Key' })
                return
            }

            if (!response.ok) {
                const text = await response.text()
                setSaveStatus({ type: 'error', message: `Error ${response.status}: ${text.slice(0, 100)}` })
                return
            }

            const data: ReverbCredentials = await response.json()
            setLoadedToken(data.api_token)
            setApiToken(data.api_token)
            setSaveStatus({ type: 'success', message: 'Saved successfully!' })
        } catch (err) {
            setSaveStatus({ type: 'error', message: `Connection error: ${err instanceof Error ? err.message : 'Unknown'}` })
        } finally {
            setIsSaving(false)
        }
    }

    // Test credentials against Reverb API
    const handleTest = async () => {
        if (!hasAdminKey) return

        setIsTesting(true)
        setTestStatus({ type: 'loading', message: 'Testing connection...' })
        setTestResult(null)

        try {
            const response = await authFetch('/api/marketplace-credentials/reverb/test', {
                method: 'POST',
            })

            if (response.status === 401) {
                setTestStatus({ type: 'error', message: 'Invalid Admin Key' })
                return
            }

            if (!response.ok) {
                const text = await response.text()
                setTestStatus({ type: 'error', message: `Error ${response.status}: ${text.slice(0, 100)}` })
                return
            }

            const data: TestResult = await response.json()
            setTestResult(data)

            if (data.ok) {
                setTestStatus({ type: 'success', message: 'Connection successful!' })
            } else {
                setTestStatus({ type: 'error', message: data.error || `HTTP ${data.status_code}` })
            }
        } catch (err) {
            setTestStatus({ type: 'error', message: `Connection error: ${err instanceof Error ? err.message : 'Unknown'}` })
        } finally {
            setIsTesting(false)
        }
    }

    // Import Reverb orders
    const handleImportOrders = async () => {
        if (!hasAdminKey) return

        setIsImporting(true)
        setImportStatus({ type: 'loading', message: 'Importing orders...' })
        setImportResult(null)

        try {
            const requestBody: Record<string, unknown> = {
                days_back: daysBack,
                limit,
                dry_run: dryRun,
                debug,
            }

            // If since_iso is provided, include it
            if (sinceIso.trim()) {
                requestBody.since_iso = sinceIso.trim()
            }

            const response = await authFetch('/api/reverb/orders/import', {
                method: 'POST',
                body: JSON.stringify(requestBody),
            })

            if (response.status === 401) {
                setImportStatus({ type: 'error', message: 'Invalid Admin Key' })
                return
            }

            if (response.status === 400) {
                const text = await response.text()
                setImportStatus({ type: 'error', message: text || 'Credentials not configured or disabled' })
                return
            }

            if (response.status === 502) {
                const text = await response.text()
                setImportStatus({ type: 'error', message: `Reverb API error: ${text.slice(0, 150)}` })
                return
            }

            if (!response.ok) {
                const text = await response.text()
                setImportStatus({ type: 'error', message: `Error ${response.status}: ${text.slice(0, 100)}` })
                return
            }

            const data: ImportResult = await response.json()
            setImportResult(data)

            if (data.total_failed === 0) {
                setImportStatus({ type: 'success', message: dryRun ? 'Dry run completed successfully!' : 'Import completed successfully!' })
            } else if (data.total_created + data.total_updated > 0) {
                setImportStatus({ type: 'success', message: `Completed with ${data.total_failed} failures` })
            } else {
                setImportStatus({ type: 'error', message: 'Import failed for all orders' })
            }
        } catch (err) {
            setImportStatus({ type: 'error', message: `Connection error: ${err instanceof Error ? err.message : 'Unknown'}` })
        } finally {
            setIsImporting(false)
        }
    }

    // Enrich Reverb orders with full details
    const handleEnrichOrders = async () => {
        if (!hasAdminKey) return

        setIsEnriching(true)
        setEnrichStatus({ type: 'loading', message: 'Enriching orders...' })
        setEnrichResult(null)

        try {
            const requestBody: Record<string, unknown> = {
                days_back: enrichDaysBack,
                limit: enrichLimit,
                dry_run: enrichDryRun,
                debug: enrichDebug,
                force: enrichForce,
            }

            if (enrichSinceIso.trim()) {
                requestBody.since_iso = enrichSinceIso.trim()
            }

            const response = await authFetch('/api/reverb/orders/enrich', {
                method: 'POST',
                body: JSON.stringify(requestBody),
            })

            if (response.status === 401) {
                setEnrichStatus({ type: 'error', message: 'Invalid Admin Key' })
                return
            }

            if (response.status === 400) {
                const text = await response.text()
                setEnrichStatus({ type: 'error', message: text || 'Credentials not configured or disabled' })
                return
            }

            if (!response.ok) {
                const text = await response.text()
                setEnrichStatus({ type: 'error', message: `Error ${response.status}: ${text.slice(0, 100)}` })
                return
            }

            const data = await response.json()
            setEnrichResult(data)

            if (data.orders_enriched > 0) {
                setEnrichStatus({ type: 'success', message: enrichDryRun ? 'Dry run completed!' : 'Enrichment completed!' })
            } else {
                setEnrichStatus({ type: 'success', message: 'No orders needed enrichment' })
            }
        } catch (err) {
            setEnrichStatus({ type: 'error', message: `Connection error: ${err instanceof Error ? err.message : 'Unknown'}` })
        } finally {
            setIsEnriching(false)
        }
    }

    // Render status alert
    const renderStatus = (status: Status, loading: boolean) => {
        if (loading) {
            return (
                <Alert severity="info" icon={<CircularProgress size={20} />}>
                    {status.message}
                </Alert>
            )
        }

        if (status.type === 'idle') return null

        const severityMap: Record<StatusType, 'success' | 'error' | 'warning' | 'info'> = {
            idle: 'info',
            loading: 'info',
            success: 'success',
            error: 'error',
            not_configured: 'warning',
        }

        return (
            <Alert severity={severityMap[status.type]} sx={{ mt: 2 }}>
                {status.message}
            </Alert>
        )
    }

    return (
        <Container maxWidth="lg">
            <Box sx={{ mb: 4 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                    <StorefrontIcon sx={{ fontSize: 40, color: 'primary.main' }} />
                    <Typography variant="h4" component="h1">
                        Marketplace Credentials
                    </Typography>
                </Box>
                <Typography variant="body1" color="text.secondary">
                    Manage API credentials for connected marketplaces.
                </Typography>
            </Box>

            {/* Admin Key Section */}
            <Paper sx={{ p: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                    Authentication
                </Typography>
                <TextField
                    label="Admin Key"
                    type="password"
                    value={adminKey}
                    onChange={(e) => setAdminKey(e.target.value)}
                    fullWidth
                    size="small"
                    helperText={hasAdminKey ? "Admin key set" : "Enter Admin Key to access credentials"}
                    sx={{ maxWidth: 400 }}
                />
                {!hasAdminKey && (
                    <Alert severity="info" sx={{ mt: 2 }}>
                        Enter your Admin Key and click <strong>Refresh</strong> to load existing credentials.
                    </Alert>
                )}
            </Paper>

            {/* Reverb Credentials Card */}
            <Card sx={{ mb: 3 }}>
                <CardHeader
                    title={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="h6">Reverb</Typography>
                            {isEnabled ? (
                                <Chip label="Enabled" color="success" size="small" />
                            ) : (
                                <Chip label="Disabled" color="default" size="small" />
                            )}
                        </Box>
                    }
                    action={
                        <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button
                                variant="outlined"
                                size="small"
                                startIcon={isRefreshing ? <CircularProgress size={16} /> : <RefreshIcon />}
                                onClick={handleRefresh}
                                disabled={!hasAdminKey || isRefreshing}
                            >
                                Refresh
                            </Button>
                            <Button
                                variant="contained"
                                size="small"
                                startIcon={isSaving ? <CircularProgress size={16} color="inherit" /> : <SaveIcon />}
                                onClick={handleSave}
                                disabled={!hasAdminKey || isSaving}
                            >
                                Save
                            </Button>
                            <Button
                                variant="outlined"
                                size="small"
                                color="secondary"
                                startIcon={isTesting ? <CircularProgress size={16} /> : <PlayArrowIcon />}
                                onClick={handleTest}
                                disabled={!hasAdminKey || isTesting}
                            >
                                Test Connection
                            </Button>
                        </Box>
                    }
                />
                <Divider />
                <CardContent>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {/* Enabled toggle */}
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={isEnabled}
                                    onChange={(e) => setIsEnabled(e.target.checked)}
                                />
                            }
                            label="Enabled"
                        />

                        {/* Base URL */}
                        <TextField
                            label="Base URL"
                            value={baseUrl}
                            onChange={(e) => setBaseUrl(e.target.value)}
                            fullWidth
                            size="small"
                            helperText="Reverb API base URL (default: https://api.reverb.com)"
                            sx={{ maxWidth: 500 }}
                        />

                        {/* API Token */}
                        <TextField
                            label="API Token"
                            type={showToken ? 'text' : 'password'}
                            value={apiToken}
                            onChange={(e) => setApiToken(e.target.value)}
                            fullWidth
                            size="small"
                            sx={{ maxWidth: 500 }}
                            InputProps={{
                                endAdornment: (
                                    <InputAdornment position="end">
                                        <IconButton
                                            onClick={() => setShowToken(!showToken)}
                                            edge="end"
                                            size="small"
                                        >
                                            {showToken ? <VisibilityOffIcon /> : <VisibilityIcon />}
                                        </IconButton>
                                    </InputAdornment>
                                ),
                            }}
                            helperText={
                                apiToken === MASKED_TOKEN
                                    ? "Token is masked. Enter a new token to update, or leave as-is to keep the existing one."
                                    : "Your Reverb API personal access token"
                            }
                        />

                        {/* Status displays */}
                        {renderStatus(refreshStatus, isRefreshing)}
                        {renderStatus(saveStatus, isSaving)}
                        {renderStatus(testStatus, isTesting)}

                        {/* Test result details */}
                        {testResult && testResult.ok && testResult.account && (
                            <Paper variant="outlined" sx={{ p: 2, mt: 1, bgcolor: 'success.light', color: 'success.contrastText' }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                    <CheckCircleIcon color="inherit" />
                                    <Typography variant="subtitle1" fontWeight="bold">
                                        Connection Verified
                                    </Typography>
                                </Box>
                                <Box sx={{ pl: 4 }}>
                                    {testResult.account.shop_name && (
                                        <Typography variant="body2">
                                            <strong>Shop:</strong> {testResult.account.shop_name}
                                        </Typography>
                                    )}
                                    {testResult.account.username && (
                                        <Typography variant="body2">
                                            <strong>Username:</strong> {testResult.account.username}
                                        </Typography>
                                    )}
                                    {testResult.account.email && (
                                        <Typography variant="body2">
                                            <strong>Email:</strong> {testResult.account.email}
                                        </Typography>
                                    )}
                                </Box>
                            </Paper>
                        )}

                        {testResult && !testResult.ok && (
                            <Paper variant="outlined" sx={{ p: 2, mt: 1, bgcolor: 'error.light', color: 'error.contrastText' }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <ErrorIcon color="inherit" />
                                    <Typography variant="subtitle1" fontWeight="bold">
                                        Connection Failed
                                    </Typography>
                                </Box>
                                <Typography variant="body2" sx={{ pl: 4 }}>
                                    {testResult.error || `HTTP ${testResult.status_code}`}
                                </Typography>
                            </Paper>
                        )}
                    </Box>
                </CardContent>
            </Card>

            {/* Reverb Orders Import Card */}
            <Card sx={{ mb: 3 }}>
                <CardHeader
                    title={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="h6">Reverb Orders Import</Typography>
                        </Box>
                    }
                    action={
                        <Button
                            variant="contained"
                            color="primary"
                            size="small"
                            startIcon={isImporting ? <CircularProgress size={16} color="inherit" /> : <DownloadIcon />}
                            onClick={handleImportOrders}
                            disabled={!hasAdminKey || isImporting}
                        >
                            Run Import
                        </Button>
                    }
                />
                <Divider />
                <CardContent>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {/* Import controls */}
                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                            <TextField
                                label="Days Back"
                                type="number"
                                value={daysBack}
                                onChange={(e) => setDaysBack(parseInt(e.target.value) || 30)}
                                size="small"
                                sx={{ width: 150 }}
                                helperText="Default: 30 days"
                                inputProps={{ min: 1, max: 365 }}
                            />
                            <TextField
                                label="Limit"
                                type="number"
                                value={limit}
                                onChange={(e) => setLimit(parseInt(e.target.value) || 50)}
                                size="small"
                                sx={{ width: 150 }}
                                helperText="Max orders"
                                inputProps={{ min: 1, max: 500 }}
                            />
                            <TextField
                                label="Since ISO (optional)"
                                value={sinceIso}
                                onChange={(e) => setSinceIso(e.target.value)}
                                size="small"
                                sx={{ width: 250 }}
                                helperText="e.g., 2025-12-01T00:00:00Z"
                                placeholder="2025-12-01T00:00:00Z"
                            />
                        </Box>

                        {/* Checkboxes */}
                        <Box sx={{ display: 'flex', gap: 2 }}>
                            <FormControlLabel
                                control={
                                    <Checkbox
                                        checked={dryRun}
                                        onChange={(e) => setDryRun(e.target.checked)}
                                    />
                                }
                                label="Dry Run (preview only)"
                            />
                            <FormControlLabel
                                control={
                                    <Checkbox
                                        checked={debug}
                                        onChange={(e) => setDebug(e.target.checked)}
                                    />
                                }
                                label="Debug (show diagnostics)"
                            />
                        </Box>

                        {/* Import status */}
                        {renderStatus(importStatus, isImporting)}

                        {/* Import results */}
                        {importResult && (
                            <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
                                <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                                    Import Results
                                </Typography>
                                <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 2 }}>
                                    <Box>
                                        <Typography variant="body2" color="text.secondary">Fetched</Typography>
                                        <Typography variant="h6">{importResult.total_fetched}</Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="body2" color="text.secondary">Created</Typography>
                                        <Typography variant="h6" color="success.main">{importResult.total_created}</Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="body2" color="text.secondary">Updated</Typography>
                                        <Typography variant="h6" color="info.main">{importResult.total_updated}</Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="body2" color="text.secondary">Failed</Typography>
                                        <Typography variant="h6" color="error.main">{importResult.total_failed}</Typography>
                                    </Box>
                                </Box>

                                {/* Failed order IDs */}
                                {importResult.failed_order_ids && importResult.failed_order_ids.length > 0 && (
                                    <Alert severity="warning" sx={{ mt: 1 }}>
                                        <strong>Failed Order IDs:</strong> {importResult.failed_order_ids.join(', ')}
                                    </Alert>
                                )}

                                {/* Preview orders table (dry run) */}
                                {importResult.preview_orders && importResult.preview_orders.length > 0 && (
                                    <Box sx={{ mt: 2 }}>
                                        <Typography variant="subtitle2" gutterBottom>
                                            Preview Orders (First {importResult.preview_orders.length})
                                        </Typography>
                                        <TableContainer>
                                            <Table size="small">
                                                <TableHead>
                                                    <TableRow>
                                                        <TableCell>Order ID</TableCell>
                                                        <TableCell>Date</TableCell>
                                                        <TableCell>Status</TableCell>
                                                        <TableCell>Currency</TableCell>
                                                        <TableCell align="right">Total</TableCell>
                                                        <TableCell align="right">Lines</TableCell>
                                                    </TableRow>
                                                </TableHead>
                                                <TableBody>
                                                    {importResult.preview_orders.map((order, idx) => (
                                                        <TableRow key={idx}>
                                                            <TableCell>{order.external_order_id}</TableCell>
                                                            <TableCell>{new Date(order.order_date).toLocaleDateString()}</TableCell>
                                                            <TableCell>{order.status_raw}</TableCell>
                                                            <TableCell>{order.currency_code}</TableCell>
                                                            <TableCell align="right">
                                                                {(order.order_total_cents / 100).toFixed(2)}
                                                            </TableCell>
                                                            <TableCell align="right">{order.line_count}</TableCell>
                                                        </TableRow>
                                                    ))}
                                                </TableBody>
                                            </Table>
                                        </TableContainer>
                                    </Box>
                                )}

                                {/* Debug fields */}
                                {debug && importResult.filter_since_utc && (
                                    <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
                                        <Typography variant="subtitle2" gutterBottom>
                                            Debug Diagnostics
                                        </Typography>
                                        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 1, fontSize: '0.875rem' }}>
                                            <Typography variant="body2" fontWeight="bold">Filter Mode:</Typography>
                                            <Typography variant="body2">{importResult.filter_mode}</Typography>

                                            <Typography variant="body2" fontWeight="bold">Filter Since (UTC):</Typography>
                                            <Typography variant="body2">{importResult.filter_since_utc}</Typography>

                                            <Typography variant="body2" fontWeight="bold">Timestamp Field:</Typography>
                                            <Typography variant="body2">{importResult.timestamp_field_used}</Typography>

                                            <Typography variant="body2" fontWeight="bold">Raw Fetched:</Typography>
                                            <Typography variant="body2">{importResult.raw_fetched}</Typography>

                                            <Typography variant="body2" fontWeight="bold">Filtered:</Typography>
                                            <Typography variant="body2">{importResult.filtered}</Typography>

                                            <Typography variant="body2" fontWeight="bold">Pages Fetched:</Typography>
                                            <Typography variant="body2">{importResult.pages_fetched}</Typography>

                                            <Typography variant="body2" fontWeight="bold">Early Stop:</Typography>
                                            <Typography variant="body2">{importResult.early_stop ? 'Yes' : 'No'}</Typography>

                                            <Typography variant="body2" fontWeight="bold">Undated Count:</Typography>
                                            <Typography variant="body2">{importResult.undated_count}</Typography>

                                            {importResult.orders_linked_to_customers !== undefined && (
                                                <>
                                                    <Box sx={{ gridColumn: '1 / -1', mt: 1, mb: 0.5, borderBottom: '1px dashed #ccc' }} />
                                                    <Typography variant="body2" fontWeight="bold" sx={{ color: 'primary.main', gridColumn: '1 / -1' }}>
                                                        Customer Linkage Stats
                                                    </Typography>

                                                    <Typography variant="body2" fontWeight="bold">Created:</Typography>
                                                    <Typography variant="body2">{importResult.customers_created}</Typography>

                                                    <Typography variant="body2" fontWeight="bold">Matched:</Typography>
                                                    <Typography variant="body2">{importResult.customers_matched}</Typography>

                                                    <Typography variant="body2" fontWeight="bold">Linked Orders:</Typography>
                                                    <Typography variant="body2">{importResult.orders_linked_to_customers}</Typography>

                                                    <Typography variant="body2" fontWeight="bold">Missing Identity:</Typography>
                                                    <Typography variant="body2" color={importResult.orders_missing_buyer_identity ? 'error.main' : 'inherit'}>
                                                        {importResult.orders_missing_buyer_identity}
                                                    </Typography>

                                                    {(importResult.orders_linked_to_customers === 0 && (importResult.total_updated + importResult.total_created > 0)) && (
                                                        <Box sx={{ gridColumn: '1 / -1', mt: 1 }}>
                                                            <Alert severity="warning">
                                                                No customers linked — check buyer identity mapping.
                                                            </Alert>
                                                        </Box>
                                                    )}
                                                </>
                                            )}
                                        </Box>
                                    </Box>
                                )}
                            </Paper>
                        )}
                    </Box>
                </CardContent>
            </Card>

            {/* Reverb Orders Enrich */}
            <Card sx={{ mt: 3 }}>
                <CardHeader
                    title="Reverb Orders Enrich"
                    subheader="Fetch full order details from Reverb API (shipping address, line items, shipments)"
                    avatar={<DownloadIcon color="primary" />}
                />
                <CardContent>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {/* Enrich Controls */}
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
                            <TextField
                                label="Days Back"
                                type="number"
                                size="small"
                                value={enrichDaysBack}
                                onChange={(e) => setEnrichDaysBack(parseInt(e.target.value) || 30)}
                                sx={{ width: 120 }}
                            />

                            <TextField
                                label="Limit"
                                type="number"
                                size="small"
                                value={enrichLimit}
                                onChange={(e) => setEnrichLimit(parseInt(e.target.value) || 50)}
                                sx={{ width: 100 }}
                            />

                            <TextField
                                label="Since ISO (optional)"
                                size="small"
                                value={enrichSinceIso}
                                onChange={(e) => setEnrichSinceIso(e.target.value)}
                                placeholder="2026-01-01T00:00:00Z"
                                sx={{ width: 220 }}
                            />

                            <FormControlLabel
                                control={<Checkbox checked={enrichDryRun} onChange={(e) => setEnrichDryRun(e.target.checked)} />}
                                label="Dry Run"
                            />

                            <FormControlLabel
                                control={<Checkbox checked={enrichDebug} onChange={(e) => setEnrichDebug(e.target.checked)} />}
                                label="Debug"
                            />

                            <FormControlLabel
                                control={<Checkbox checked={enrichForce} onChange={(e) => setEnrichForce(e.target.checked)} />}
                                label="Force Overwrite"
                            />

                            <Button
                                variant="contained"
                                color="secondary"
                                startIcon={isEnriching ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />}
                                onClick={handleEnrichOrders}
                                disabled={!hasAdminKey || isEnriching}
                            >
                                Run Enrich
                            </Button>
                        </Box>

                        {/* Enrich Status */}
                        {renderStatus(enrichStatus, isEnriching)}

                        {/* Enrich Results */}
                        {enrichResult && (
                            <Paper variant="outlined" sx={{ p: 2 }}>
                                <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                                    <Box>
                                        <Typography variant="body2" color="text.secondary">Scanned</Typography>
                                        <Typography variant="h6">{enrichResult.orders_scanned}</Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="body2" color="text.secondary">Enriched</Typography>
                                        <Typography variant="h6" color="success.main">{enrichResult.orders_enriched}</Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="body2" color="text.secondary">Skipped</Typography>
                                        <Typography variant="h6">{enrichResult.orders_skipped}</Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="body2" color="text.secondary">Addresses</Typography>
                                        <Typography variant="h6">{enrichResult.addresses_upserted}</Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="body2" color="text.secondary">Lines</Typography>
                                        <Typography variant="h6">{enrichResult.lines_upserted}</Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="body2" color="text.secondary">Shipments</Typography>
                                        <Typography variant="h6">{enrichResult.shipments_upserted}</Typography>
                                    </Box>
                                </Box>

                                {/* Failed order IDs */}
                                {enrichResult.failed_order_ids && Object.keys(enrichResult.failed_order_ids).length > 0 && (
                                    <Alert severity="warning" sx={{ mt: 1 }}>
                                        <strong>Failed Orders:</strong>{' '}
                                        {Object.entries(enrichResult.failed_order_ids).map(([id, err]) => `${id}: ${err}`).join(', ')}
                                    </Alert>
                                )}

                                {/* Preview orders */}
                                {enrichResult.preview_orders && enrichResult.preview_orders.length > 0 && (
                                    <Box sx={{ mt: 2 }}>
                                        <Typography variant="subtitle2" gutterBottom>
                                            Preview (First {enrichResult.preview_orders.length})
                                        </Typography>
                                        <TableContainer>
                                            <Table size="small">
                                                <TableHead>
                                                    <TableRow>
                                                        <TableCell>Order ID</TableCell>
                                                        <TableCell>Buyer</TableCell>
                                                        <TableCell>Shipping</TableCell>
                                                        <TableCell>Lines</TableCell>
                                                        <TableCell>Shipments</TableCell>
                                                    </TableRow>
                                                </TableHead>
                                                <TableBody>
                                                    {enrichResult.preview_orders.map((order, idx) => (
                                                        <TableRow key={idx}>
                                                            <TableCell>{order.external_order_id}</TableCell>
                                                            <TableCell>{order.buyer_email || '—'}</TableCell>
                                                            <TableCell>
                                                                {order.shipping
                                                                    ? `${order.shipping.city || ''}, ${order.shipping.postal_code || ''} ${order.shipping.country_code || ''}`
                                                                    : '—'}
                                                            </TableCell>
                                                            <TableCell>
                                                                {order.lines?.length || 0} item(s)
                                                            </TableCell>
                                                            <TableCell>
                                                                {order.shipments?.map((s, i) => (
                                                                    <span key={i}>{s.carrier}: {s.tracking_number || 'no tracking'}</span>
                                                                )) || '—'}
                                                            </TableCell>
                                                        </TableRow>
                                                    ))}
                                                </TableBody>
                                            </Table>
                                        </TableContainer>
                                    </Box>
                                )}
                            </Paper>
                        )}
                    </Box>
                </CardContent>
            </Card>

            {/* Placeholder for future marketplaces */}
            <Paper sx={{ p: 3, textAlign: 'center', bgcolor: 'grey.100' }}>
                <Typography variant="body2" color="text.secondary">
                    Additional marketplaces (Amazon, eBay, Etsy) coming soon.
                </Typography>
            </Paper>
        </Container>
    )
}
