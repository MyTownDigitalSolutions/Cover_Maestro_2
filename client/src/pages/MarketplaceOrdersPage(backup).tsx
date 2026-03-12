import { useState } from 'react'
import {
    Box, Typography, Container, TextField, Button, Paper, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, MenuItem, Alert, CircularProgress, Dialog,
    DialogTitle, DialogContent, DialogActions, Divider, Chip, IconButton, Autocomplete, Checkbox
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import ListAltIcon from '@mui/icons-material/ListAlt'
import CleaningServicesIcon from '@mui/icons-material/CleaningServices'
import EditIcon from '@mui/icons-material/Edit'
import CheckIcon from '@mui/icons-material/Check'
import CloseIcon from '@mui/icons-material/Close'
import ReceiptIcon from '@mui/icons-material/Receipt'

import { customersApi } from '../services/api'
import type { Customer } from '../types'

interface MarketplaceOrder {
    id: number
    marketplace: string
    source: string
    external_order_id: string
    external_order_number?: string
    order_date: string
    status_raw?: string
    status_normalized?: string
    buyer_name?: string
    buyer_email?: string
    order_total_cents?: number
    currency_code?: string
    created_at: string
    customer_id?: number
}

interface OrderAddress {
    id: number
    address_type: string
    name?: string
    line1?: string
    line2?: string
    city?: string
    state_or_region?: string
    postal_code?: string
    country_code?: string
    phone?: string
}

interface OrderLine {
    id: number
    external_line_item_id?: string
    sku?: string
    title?: string
    quantity: number
    unit_price_cents?: number
    line_total_cents?: number
    product_id?: string
    model_id?: number
    // Resolved fields from backend
    resolved_model_id?: number
    resolved_model_name?: string
    resolved_manufacturer_name?: string
    resolved_series_name?: string
}

interface ModelSearchResult {
    id: number
    name: string
    manufacturer_name?: string
    series_name?: string
    reverb_product_id?: string
    // Fields from marketplace-lookup endpoint
    model_id?: number
    model_name?: string
    sku?: string
    matched_listing_marketplace?: string
    matched_listing_identifier?: string
}

interface OrderShipment {
    id: number
    carrier?: string
    tracking_number?: string
    shipped_at?: string
}

interface CleanupResult {
    dry_run: boolean
    marketplace: string
    order_id: number | null
    mode: string
    rows_scanned: number
    duplicate_groups_found: number
    rows_to_delete: number
    rows_deleted: number
    affected_order_ids_sample: number[]
}

interface OrderDetail extends MarketplaceOrder {
    addresses: OrderAddress[]
    lines: OrderLine[]
    shipments: OrderShipment[]
}

export default function MarketplaceOrdersPage() {
    // Filter state
    const [marketplace, setMarketplace] = useState('all')
    const [statusFilter, setStatusFilter] = useState('all')
    const [buyerEmail, setBuyerEmail] = useState('')
    const [dateFrom, setDateFrom] = useState('')
    const [dateTo, setDateTo] = useState('')
    const [limit, setLimit] = useState(50)

    // Results state
    const [orders, setOrders] = useState<MarketplaceOrder[]>([])
    const [isSearching, setIsSearching] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Detail dialog state
    const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null)
    const [orderDetail, setOrderDetail] = useState<OrderDetail | null>(null)
    const [linkedCustomer, setLinkedCustomer] = useState<Customer | null>(null)
    const [isLoadingDetail, setIsLoadingDetail] = useState(false)
    const [detailError, setDetailError] = useState<string | null>(null)

    // Admin key state
    const [adminKey, setAdminKey] = useState('')

    // Cleanup state
    const [cleanupLoadingPreview, setCleanupLoadingPreview] = useState(false)
    const [cleanupLoadingRun, setCleanupLoadingRun] = useState(false)
    const [cleanupPreviewResult, setCleanupPreviewResult] = useState<CleanupResult | null>(null)
    const [cleanupRunResult, setCleanupRunResult] = useState<CleanupResult | null>(null)
    const [cleanupError, setCleanupError] = useState<string | null>(null)
    const [cleanupPreviewOrderId, setCleanupPreviewOrderId] = useState<number | null>(null)

    // Line edit state
    const [editingLineId, setEditingLineId] = useState<number | null>(null)
    const [editProductId, setEditProductId] = useState('')
    const [editModelId, setEditModelId] = useState<number | null>(null)
    const [lineEditLoading, setLineEditLoading] = useState(false)
    const [lineEditError, setLineEditError] = useState<string | null>(null)
    const [, setModelSearchQuery] = useState('')
    const [modelSearchResults, setModelSearchResults] = useState<ModelSearchResult[]>([])
    const [modelSearchLoading, setModelSearchLoading] = useState(false)

    // Order selection state (for invoice generation)
    const [selectedOrderIds, setSelectedOrderIds] = useState<number[]>([])
    const [invoiceLoading, setInvoiceLoading] = useState(false)

    const handleSearch = async () => {
        setIsSearching(true)
        setError(null)
        setOrders([])

        try {
            const params = new URLSearchParams()
            if (marketplace !== 'all') params.append('marketplace', marketplace)
            if (statusFilter !== 'all') params.append('status_normalized', statusFilter)
            if (buyerEmail.trim()) params.append('buyer_email', buyerEmail.trim())
            if (dateFrom) params.append('date_from', dateFrom)
            if (dateTo) params.append('date_to', dateTo)
            params.append('limit', limit.toString())

            const response = await fetch(`/api/marketplace-orders?${params.toString()}`)

            if (!response.ok) {
                const text = await response.text()
                throw new Error(`Error ${response.status}: ${text.slice(0, 100)}`)
            }

            const data: MarketplaceOrder[] = await response.json()
            setOrders(data)

            if (data.length === 0) {
                setError('No orders found matching the criteria.')
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error occurred')
        } finally {
            setIsSearching(false)
        }
    }

    const handleRowClick = async (orderId: number) => {
        setSelectedOrderId(orderId)
        setIsLoadingDetail(true)
        setDetailError(null)
        setOrderDetail(null)
        setLinkedCustomer(null)

        try {
            const response = await fetch(`/api/marketplace-orders/${orderId}`)

            if (!response.ok) {
                const text = await response.text()
                throw new Error(`Error ${response.status}: ${text.slice(0, 100)}`)
            }

            const data: OrderDetail = await response.json()
            setOrderDetail(data)

            // Fetch linked customer if present
            if (data.customer_id) {
                try {
                    const customer = await customersApi.get(data.customer_id)
                    setLinkedCustomer(customer)
                } catch (customerErr) {
                    console.error("Failed to load customer details", customerErr)
                    // Don't fail the whole view if customer fetch fails
                }
            }
        } catch (err) {
            setDetailError(err instanceof Error ? err.message : 'Failed to load order details')
        } finally {
            setIsLoadingDetail(false)
        }
    }

    const handleCloseDetail = () => {
        setSelectedOrderId(null)
        setOrderDetail(null)
        setLinkedCustomer(null)
        setDetailError(null)
        // Reset cleanup state when closing
        setCleanupPreviewResult(null)
        setCleanupRunResult(null)
        setCleanupError(null)
        setCleanupPreviewOrderId(null)
        // Reset line edit state when closing
        setEditingLineId(null)
        setEditProductId('')
        setEditModelId(null)
        setLineEditError(null)
    }

    const handleStartLineEdit = async (line: OrderLine) => {
        setEditingLineId(line.id)
        setEditProductId(line.product_id || '')
        setEditModelId(line.resolved_model_id || null)
        setLineEditError(null)
        setModelSearchResults([]) // Clear previous results

        // If order is Reverb and product_id exists, pre-load marketplace lookup results
        if (orderDetail?.marketplace?.toLowerCase() === 'reverb' && line.product_id) {
            setModelSearchLoading(true)
            try {
                const response = await fetch(
                    `/api/models/marketplace-lookup?marketplace=reverb&identifier=${encodeURIComponent(line.product_id)}`
                )
                if (response.ok) {
                    const data = await response.json()
                    // Convert marketplace-lookup response to ModelSearchResult format
                    const results: ModelSearchResult[] = data.map((item: any) => ({
                        id: item.model_id,
                        name: item.model_name,
                        manufacturer_name: item.manufacturer_name,
                        series_name: item.series_name,
                        sku: item.sku,
                        matched_listing_marketplace: item.matched_listing_marketplace,
                        matched_listing_identifier: item.matched_listing_identifier
                    }))
                    setModelSearchResults(results)
                }
            } catch (err) {
                console.error('Marketplace lookup failed:', err)
            } finally {
                setModelSearchLoading(false)
            }
        }
    }

    const handleCancelLineEdit = () => {
        setEditingLineId(null)
        setEditProductId('')
        setEditModelId(null)
        setLineEditError(null)
    }

    const handleSaveLineEdit = async () => {
        if (!editingLineId || !adminKey.trim()) {
            setLineEditError('Admin key is required')
            return
        }

        setLineEditLoading(true)
        setLineEditError(null)

        try {
            const response = await fetch(`/api/marketplace-orders/lines/${editingLineId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Admin-Key': adminKey.trim()
                },
                body: JSON.stringify({
                    product_id: editProductId || null,
                    model_id: editModelId || 0  // 0 clears the model_id
                })
            })

            if (!response.ok) {
                const text = await response.text()
                throw new Error(`Error ${response.status}: ${text.slice(0, 100)}`)
            }

            // Re-fetch order detail to get updated resolved fields
            if (orderDetail) {
                const detailResponse = await fetch(`/api/marketplace-orders/${orderDetail.id}`)
                if (detailResponse.ok) {
                    const detailData: OrderDetail = await detailResponse.json()
                    setOrderDetail(detailData)
                }
            }

            handleCancelLineEdit()
        } catch (err) {
            setLineEditError(err instanceof Error ? err.message : 'Failed to save')
        } finally {
            setLineEditLoading(false)
        }
    }

    const searchModels = async (query: string) => {
        if (!query.trim()) {
            setModelSearchResults([])
            return
        }

        setModelSearchLoading(true)
        setModelSearchQuery(query)

        try {
            const response = await fetch(`/api/models/search?q=${encodeURIComponent(query)}&limit=10`)
            if (response.ok) {
                const data: ModelSearchResult[] = await response.json()
                setModelSearchResults(data)
            }
        } catch (err) {
            console.error('Model search failed:', err)
        } finally {
            setModelSearchLoading(false)
        }
    }

    // Order selection handlers
    const handleOrderSelect = (orderId: number, checked: boolean) => {
        if (checked) {
            setSelectedOrderIds(prev => [...prev, orderId])
        } else {
            setSelectedOrderIds(prev => prev.filter(id => id !== orderId))
        }
    }

    const handleSelectAll = (checked: boolean) => {
        if (checked) {
            setSelectedOrderIds(orders.map(o => o.id))
        } else {
            setSelectedOrderIds([])
        }
    }

    const handleGenerateInvoice = async (orderIds?: number[]) => {
        const idsToGenerate = orderIds || selectedOrderIds
        if (idsToGenerate.length === 0) {
            setError('Please select at least one order')
            return
        }
        if (!adminKey.trim()) {
            setError('Admin key is required for invoice generation')
            return
        }

        setInvoiceLoading(true)
        setError(null)

        try {
            const response = await fetch('/api/marketplace-orders/invoice', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Admin-Key': adminKey.trim()
                },
                body: JSON.stringify({
                    order_ids: idsToGenerate,
                    mode: 'html'
                })
            })

            if (!response.ok) {
                const text = await response.text()
                throw new Error(`Error ${response.status}: ${text.slice(0, 100)}`)
            }

            const data = await response.json()

            // Open invoice in new tab
            const invoiceWindow = window.open('', '_blank')
            if (invoiceWindow) {
                invoiceWindow.document.write(data.html)
                invoiceWindow.document.close()
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Invoice generation failed')
        } finally {
            setInvoiceLoading(false)
        }
    }

    const handleCleanupShipmentsPreview = async () => {
        if (!orderDetail || !adminKey.trim()) {
            setCleanupError('Admin key is required for cleanup operations.')
            return
        }

        setCleanupLoadingPreview(true)
        setCleanupError(null)
        setCleanupPreviewResult(null)
        setCleanupRunResult(null)

        try {
            const response = await fetch('/api/marketplace-orders/cleanup-shipments', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Admin-Key': adminKey.trim()
                },
                body: JSON.stringify({
                    marketplace: orderDetail.marketplace,
                    order_id: orderDetail.id,
                    mode: 'prefer_tracked',
                    dry_run: true
                })
            })

            if (!response.ok) {
                const text = await response.text()
                throw new Error(`Error ${response.status}: ${text.slice(0, 150)}`)
            }

            const data: CleanupResult = await response.json()
            setCleanupPreviewResult(data)
            setCleanupPreviewOrderId(orderDetail.id)
        } catch (err) {
            setCleanupError(err instanceof Error ? err.message : 'Cleanup preview failed')
        } finally {
            setCleanupLoadingPreview(false)
        }
    }

    const handleCleanupShipmentsRun = async () => {
        if (!orderDetail || !adminKey.trim()) {
            setCleanupError('Admin key is required for cleanup operations.')
            return
        }

        setCleanupLoadingRun(true)
        setCleanupError(null)
        setCleanupRunResult(null)

        try {
            const response = await fetch('/api/marketplace-orders/cleanup-shipments', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Admin-Key': adminKey.trim()
                },
                body: JSON.stringify({
                    marketplace: orderDetail.marketplace,
                    order_id: orderDetail.id,
                    mode: 'prefer_tracked',
                    dry_run: false
                })
            })

            if (!response.ok) {
                const text = await response.text()
                throw new Error(`Error ${response.status}: ${text.slice(0, 150)}`)
            }

            const data: CleanupResult = await response.json()
            setCleanupRunResult(data)

            // Re-fetch order detail to update shipments list
            const detailResponse = await fetch(`/api/marketplace-orders/${orderDetail.id}`)
            if (detailResponse.ok) {
                const detailData: OrderDetail = await detailResponse.json()
                setOrderDetail(detailData)
            }
        } catch (err) {
            setCleanupError(err instanceof Error ? err.message : 'Cleanup run failed')
        } finally {
            setCleanupLoadingRun(false)
        }
    }

    // Check if cleanup confirm button should be enabled
    const canRunCleanup = cleanupPreviewResult !== null &&
        cleanupPreviewOrderId === orderDetail?.id &&
        cleanupPreviewResult.rows_to_delete > 0 &&
        !cleanupLoadingRun

    const formatCurrency = (cents?: number, currency?: string) => {
        if (cents === null || cents === undefined) return '—'
        const dollars = cents / 100
        return `${currency || 'USD'} ${dollars.toFixed(2)}`
    }

    const formatDate = (dateStr: string) => {
        try {
            return new Date(dateStr).toLocaleString()
        } catch {
            return dateStr
        }
    }

    return (
        <Container maxWidth="xl">
            <Box sx={{ mb: 4 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                    <ListAltIcon sx={{ fontSize: 40, color: 'primary.main' }} />
                    <Typography variant="h4" component="h1">
                        Marketplace Orders
                    </Typography>
                </Box>
                <Typography variant="body1" color="text.secondary">
                    View and search orders imported from connected marketplaces.
                </Typography>
            </Box>

            {/* Admin Key Input */}
            <Paper sx={{ p: 2, mb: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <TextField
                        label="Admin Key"
                        type="password"
                        value={adminKey}
                        onChange={(e) => setAdminKey(e.target.value)}
                        size="small"
                        sx={{ width: 300 }}
                        placeholder="Required for cleanup operations"
                    />
                    <Typography variant="body2" color="text.secondary">
                        Admin key is required for shipment cleanup operations in order detail.
                    </Typography>
                </Box>
            </Paper>

            {/* Filters */}
            <Paper sx={{ p: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                    Filters
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
                    <TextField
                        select
                        label="Marketplace"
                        value={marketplace}
                        onChange={(e) => setMarketplace(e.target.value)}
                        size="small"
                        sx={{ width: 150 }}
                    >
                        <MenuItem value="all">All</MenuItem>
                        <MenuItem value="reverb">Reverb</MenuItem>
                        <MenuItem value="amazon">Amazon</MenuItem>
                        <MenuItem value="ebay">eBay</MenuItem>
                        <MenuItem value="etsy">Etsy</MenuItem>
                    </TextField>

                    <TextField
                        select
                        label="Status"
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        size="small"
                        sx={{ width: 150 }}
                    >
                        <MenuItem value="all">All</MenuItem>
                        <MenuItem value="pending">Pending</MenuItem>
                        <MenuItem value="processing">Processing</MenuItem>
                        <MenuItem value="shipped">Shipped</MenuItem>
                        <MenuItem value="delivered">Delivered</MenuItem>
                        <MenuItem value="cancelled">Cancelled</MenuItem>
                        <MenuItem value="unknown">Unknown</MenuItem>
                    </TextField>

                    <TextField
                        label="Buyer Email"
                        value={buyerEmail}
                        onChange={(e) => setBuyerEmail(e.target.value)}
                        size="small"
                        sx={{ width: 250 }}
                        placeholder="Search by email"
                    />

                    <TextField
                        label="Date From"
                        type="date"
                        value={dateFrom}
                        onChange={(e) => setDateFrom(e.target.value)}
                        size="small"
                        InputLabelProps={{ shrink: true }}
                        sx={{ width: 180 }}
                    />

                    <TextField
                        label="Date To"
                        type="date"
                        value={dateTo}
                        onChange={(e) => setDateTo(e.target.value)}
                        size="small"
                        InputLabelProps={{ shrink: true }}
                        sx={{ width: 180 }}
                    />

                    <TextField
                        label="Limit"
                        type="number"
                        value={limit}
                        onChange={(e) => setLimit(parseInt(e.target.value) || 50)}
                        size="small"
                        sx={{ width: 100 }}
                        inputProps={{ min: 1, max: 500 }}
                    />
                </Box>

                <Button
                    variant="contained"
                    startIcon={isSearching ? <CircularProgress size={16} color="inherit" /> : <SearchIcon />}
                    onClick={handleSearch}
                    disabled={isSearching}
                >
                    Search
                </Button>
            </Paper>

            {/* Error display */}
            {error && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                    {error}
                </Alert>
            )}

            {/* Results table */}
            {orders.length > 0 && (
                <>
                    {/* Selection actions bar */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                        <Typography variant="body2" color="text.secondary">
                            {selectedOrderIds.length > 0
                                ? `${selectedOrderIds.length} order(s) selected`
                                : 'Select orders to generate invoice'}
                        </Typography>
                        <Button
                            variant="contained"
                            startIcon={invoiceLoading ? <CircularProgress size={16} /> : <ReceiptIcon />}
                            onClick={() => handleGenerateInvoice()}
                            disabled={selectedOrderIds.length === 0 || invoiceLoading || !adminKey.trim()}
                        >
                            Generate Invoice
                        </Button>
                    </Box>
                    <TableContainer component={Paper}>
                        <Table>
                            <TableHead>
                                <TableRow>
                                    <TableCell padding="checkbox">
                                        <Checkbox
                                            checked={orders.length > 0 && selectedOrderIds.length === orders.length}
                                            indeterminate={selectedOrderIds.length > 0 && selectedOrderIds.length < orders.length}
                                            onChange={(e) => handleSelectAll(e.target.checked)}
                                        />
                                    </TableCell>
                                    <TableCell>Order Date</TableCell>
                                    <TableCell>Marketplace</TableCell>
                                    <TableCell>Order ID</TableCell>
                                    <TableCell>Status</TableCell>
                                    <TableCell>Buyer Email</TableCell>
                                    <TableCell align="right">Total</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {orders.map((order) => (
                                    <TableRow
                                        key={order.id}
                                        hover
                                        sx={{ cursor: 'pointer' }}
                                    >
                                        <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                                            <Checkbox
                                                checked={selectedOrderIds.includes(order.id)}
                                                onChange={(e) => handleOrderSelect(order.id, e.target.checked)}
                                            />
                                        </TableCell>
                                        <TableCell onClick={() => handleRowClick(order.id)}>{formatDate(order.order_date)}</TableCell>
                                        <TableCell onClick={() => handleRowClick(order.id)}>
                                            <Chip label={order.marketplace} size="small" color="primary" variant="outlined" />
                                        </TableCell>
                                        <TableCell onClick={() => handleRowClick(order.id)}>{order.external_order_number || order.external_order_id}</TableCell>
                                        <TableCell onClick={() => handleRowClick(order.id)}>
                                            {order.status_normalized || order.status_raw || '—'}
                                        </TableCell>
                                        <TableCell onClick={() => handleRowClick(order.id)}>{order.buyer_email || '—'}</TableCell>
                                        <TableCell align="right" onClick={() => handleRowClick(order.id)}>
                                            {formatCurrency(order.order_total_cents, order.currency_code)}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </>
            )}

            {/* Order Detail Dialog */}
            <Dialog
                open={selectedOrderId !== null}
                onClose={handleCloseDetail}
                maxWidth="md"
                fullWidth
            >
                <DialogTitle>
                    Order Details
                    {orderDetail && (
                        <Typography variant="body2" color="text.secondary">
                            {orderDetail.marketplace} - {orderDetail.external_order_number || orderDetail.external_order_id}
                        </Typography>
                    )}
                </DialogTitle>
                <DialogContent>
                    {isLoadingDetail && (
                        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                            <CircularProgress />
                        </Box>
                    )}

                    {detailError && (
                        <Alert severity="error" sx={{ mb: 2 }}>
                            {detailError}
                        </Alert>
                    )}

                    {orderDetail && !isLoadingDetail && (
                        <Box>
                            {/* Order Info */}
                            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                                Order Information
                            </Typography>
                            <Box sx={{ mb: 3, pl: 2 }}>
                                <Typography variant="body2"><strong>Buyer:</strong> {orderDetail.buyer_name || '—'}</Typography>
                                <Typography variant="body2"><strong>Email:</strong> {orderDetail.buyer_email || '—'}</Typography>
                                <Typography variant="body2"><strong>Order Date:</strong> {formatDate(orderDetail.order_date)}</Typography>
                                <Typography variant="body2"><strong>Status:</strong> {orderDetail.status_normalized || orderDetail.status_raw || '—'}</Typography>
                                <Typography variant="body2"><strong>Total:</strong> {formatCurrency(orderDetail.order_total_cents, orderDetail.currency_code)}</Typography>
                            </Box>

                            <Divider sx={{ my: 2 }} />

                            {/* Customer Link */}
                            {linkedCustomer && (
                                <>
                                    <Box sx={{ mb: 2 }}>
                                        <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                                            Customer
                                        </Typography>
                                        <Box sx={{ pl: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <Typography variant="body1" fontWeight="medium">
                                                {linkedCustomer.name}
                                            </Typography>
                                            <Chip size="small" label="Linked" color="success" variant="outlined" />
                                        </Box>
                                        {(linkedCustomer.buyer_email || linkedCustomer.marketplace_buyer_email) && (
                                            <Box sx={{ pl: 2, mt: 0.5 }}>
                                                {linkedCustomer.buyer_email && (
                                                    <Typography variant="body2">{linkedCustomer.buyer_email}</Typography>
                                                )}
                                                {linkedCustomer.marketplace_buyer_email && (
                                                    <Typography variant="body2" color="text.secondary">
                                                        Proxy: {linkedCustomer.marketplace_buyer_email}
                                                    </Typography>
                                                )}
                                            </Box>
                                        )}
                                    </Box>
                                    <Divider sx={{ my: 2 }} />
                                </>
                            )}

                            {/* Addresses */}
                            {orderDetail.addresses && orderDetail.addresses.length > 0 && (
                                <>
                                    <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                                        Addresses
                                    </Typography>
                                    {orderDetail.addresses.map((addr) => (
                                        <Box key={addr.id} sx={{ mb: 2, pl: 2 }}>
                                            <Typography variant="body2" color="primary">
                                                <strong>{addr.address_type.toUpperCase()}</strong>
                                            </Typography>
                                            <Typography variant="body2">{addr.name}</Typography>
                                            <Typography variant="body2">{addr.line1}</Typography>
                                            {addr.line2 && <Typography variant="body2">{addr.line2}</Typography>}
                                            <Typography variant="body2">
                                                {addr.city}, {addr.state_or_region} {addr.postal_code}
                                            </Typography>
                                            <Typography variant="body2">{addr.country_code}</Typography>
                                            {addr.phone && <Typography variant="body2">Phone: {addr.phone}</Typography>}
                                        </Box>
                                    ))}
                                    <Divider sx={{ my: 2 }} />
                                </>
                            )}

                            {/* Order Lines */}
                            {orderDetail.lines && orderDetail.lines.length > 0 && (
                                <>
                                    <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                                        Line Items
                                    </Typography>
                                    {orderDetail.lines.map((line) => (
                                        <Paper key={line.id} variant="outlined" sx={{ p: 2, mb: 2 }}>
                                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                                                <Box>
                                                    <Typography variant="body2" fontWeight="bold">
                                                        {line.title || line.sku || '—'}
                                                    </Typography>
                                                    <Typography variant="body2" color="text.secondary">
                                                        SKU: {line.sku || '—'} | Qty: {line.quantity} | {formatCurrency(line.line_total_cents, orderDetail.currency_code)}
                                                    </Typography>
                                                </Box>
                                                {editingLineId !== line.id && (
                                                    <IconButton size="small" onClick={() => handleStartLineEdit(line)} disabled={!adminKey.trim()}>
                                                        <EditIcon fontSize="small" />
                                                    </IconButton>
                                                )}
                                            </Box>

                                            {/* Resolved Model Info */}
                                            {line.resolved_model_name ? (
                                                <Box sx={{ mb: 1, p: 1, bgcolor: 'success.50', borderRadius: 1, border: '1px solid', borderColor: 'success.light' }}>
                                                    <Typography variant="body2" color="success.dark">
                                                        <strong>Linked:</strong> {line.resolved_manufacturer_name} / {line.resolved_series_name} / {line.resolved_model_name}
                                                    </Typography>
                                                </Box>
                                            ) : (
                                                <Chip label="Unmatched" size="small" color="warning" variant="outlined" sx={{ mb: 1 }} />
                                            )}

                                            {/* Reverb Product ID */}
                                            <Typography variant="caption" color="text.secondary">
                                                Reverb Product ID: {line.product_id || '—'}
                                            </Typography>

                                            {/* Edit Mode */}
                                            {editingLineId === line.id && (
                                                <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                                                    <Typography variant="body2" fontWeight="bold" gutterBottom>
                                                        Edit Line Mapping
                                                    </Typography>

                                                    {lineEditError && (
                                                        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setLineEditError(null)}>
                                                            {lineEditError}
                                                        </Alert>
                                                    )}

                                                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                                        <TextField
                                                            label="Reverb Product ID"
                                                            value={editProductId}
                                                            onChange={(e) => setEditProductId(e.target.value)}
                                                            size="small"
                                                            fullWidth
                                                        />

                                                        <Autocomplete
                                                            options={modelSearchResults}
                                                            getOptionLabel={(option) =>
                                                                `${option.manufacturer_name || ''} / ${option.series_name || ''} / ${option.name}`
                                                            }
                                                            loading={modelSearchLoading}
                                                            value={modelSearchResults.find(m => m.id === editModelId) || null}
                                                            onInputChange={(_, value) => searchModels(value)}
                                                            onChange={(_, value) => setEditModelId(value?.id || null)}
                                                            renderInput={(params) => (
                                                                <TextField
                                                                    {...params}
                                                                    label="Link to Model"
                                                                    size="small"
                                                                    placeholder="Search models..."
                                                                />
                                                            )}
                                                            renderOption={(props, option) => (
                                                                <li {...props} key={option.id}>
                                                                    <Box>
                                                                        <Typography variant="body2">
                                                                            {option.manufacturer_name} / {option.series_name} / {option.name}
                                                                        </Typography>
                                                                        {option.reverb_product_id && (
                                                                            <Typography variant="caption" color="text.secondary">
                                                                                Reverb ID: {option.reverb_product_id}
                                                                            </Typography>
                                                                        )}
                                                                    </Box>
                                                                </li>
                                                            )}
                                                        />

                                                        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                                                            <Button
                                                                size="small"
                                                                onClick={handleCancelLineEdit}
                                                                startIcon={<CloseIcon />}
                                                            >
                                                                Cancel
                                                            </Button>
                                                            <Button
                                                                size="small"
                                                                variant="contained"
                                                                onClick={handleSaveLineEdit}
                                                                disabled={lineEditLoading}
                                                                startIcon={lineEditLoading ? <CircularProgress size={16} /> : <CheckIcon />}
                                                            >
                                                                Save
                                                            </Button>
                                                        </Box>
                                                    </Box>
                                                </Box>
                                            )}
                                        </Paper>
                                    ))}
                                    <Divider sx={{ my: 2 }} />
                                </>
                            )}

                            {/* Shipments */}
                            {orderDetail.shipments && orderDetail.shipments.length > 0 && (
                                <>
                                    <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                                        Shipments
                                    </Typography>
                                    {orderDetail.shipments.map((shipment) => (
                                        <Box key={shipment.id} sx={{ mb: 1, pl: 2 }}>
                                            <Typography variant="body2">
                                                <strong>Carrier:</strong> {shipment.carrier || '—'}
                                            </Typography>
                                            <Typography variant="body2">
                                                <strong>Tracking:</strong> {shipment.tracking_number || '—'}
                                            </Typography>
                                            {shipment.shipped_at && (
                                                <Typography variant="body2">
                                                    <strong>Shipped:</strong> {formatDate(shipment.shipped_at)}
                                                </Typography>
                                            )}
                                        </Box>
                                    ))}
                                </>
                            )}

                            <Divider sx={{ my: 2 }} />

                            {/* Shipment Cleanup Section */}
                            <Typography variant="subtitle1" fontWeight="bold" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <CleaningServicesIcon fontSize="small" />
                                Shipment Cleanup (Prefer Tracked)
                            </Typography>
                            <Box sx={{ pl: 2 }}>
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                    Remove duplicate shipment rows that have no tracking number when a tracked shipment exists for the same carrier.
                                </Typography>

                                {!adminKey.trim() && (
                                    <Alert severity="info" sx={{ mb: 2 }}>
                                        Enter an Admin Key at the top of the page to enable cleanup operations.
                                    </Alert>
                                )}

                                {cleanupError && (
                                    <Alert severity="error" sx={{ mb: 2 }}>
                                        {cleanupError}
                                    </Alert>
                                )}

                                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                                    <Button
                                        variant="outlined"
                                        onClick={handleCleanupShipmentsPreview}
                                        disabled={!adminKey.trim() || cleanupLoadingPreview || cleanupLoadingRun}
                                        startIcon={cleanupLoadingPreview ? <CircularProgress size={16} /> : undefined}
                                    >
                                        Preview Cleanup
                                    </Button>
                                    <Button
                                        variant="contained"
                                        color="warning"
                                        onClick={handleCleanupShipmentsRun}
                                        disabled={!canRunCleanup}
                                        startIcon={cleanupLoadingRun ? <CircularProgress size={16} color="inherit" /> : undefined}
                                    >
                                        Run Cleanup
                                    </Button>
                                </Box>

                                {/* Preview Results */}
                                {cleanupPreviewResult && cleanupPreviewOrderId === orderDetail.id && (
                                    <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                                        <Typography variant="body2" fontWeight="bold" gutterBottom>
                                            Preview Results (Dry Run)
                                        </Typography>
                                        <Typography variant="body2">Rows Scanned: {cleanupPreviewResult.rows_scanned}</Typography>
                                        <Typography variant="body2">Duplicate Groups Found: {cleanupPreviewResult.duplicate_groups_found}</Typography>
                                        <Typography variant="body2" color={cleanupPreviewResult.rows_to_delete > 0 ? 'warning.main' : 'text.secondary'}>
                                            Rows to Delete: {cleanupPreviewResult.rows_to_delete}
                                        </Typography>
                                        {cleanupPreviewResult.rows_to_delete === 0 && (
                                            <Typography variant="body2" color="success.main" sx={{ mt: 1 }}>
                                                ✓ Nothing to delete. All shipments are clean.
                                            </Typography>
                                        )}
                                    </Paper>
                                )}

                                {/* Run Results */}
                                {cleanupRunResult && (
                                    <Paper variant="outlined" sx={{ p: 2, bgcolor: 'success.50', borderColor: 'success.main' }}>
                                        <Typography variant="body2" fontWeight="bold" gutterBottom color="success.main">
                                            Cleanup Complete
                                        </Typography>
                                        <Typography variant="body2">Rows Deleted: {cleanupRunResult.rows_deleted}</Typography>
                                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                            Shipments list has been refreshed.
                                        </Typography>
                                    </Paper>
                                )}
                            </Box>
                        </Box>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseDetail}>Close</Button>
                </DialogActions>
            </Dialog>
        </Container>
    )
}
