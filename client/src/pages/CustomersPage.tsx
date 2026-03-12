import { useEffect, useState } from 'react'
import {
  Box, Typography, Paper, Button, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, Grid, IconButton, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Chip, Divider,
  CircularProgress, Collapse
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import AddIcon from '@mui/icons-material/Add'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import ReceiptIcon from '@mui/icons-material/Receipt'
import { customersApi } from '../services/api'
import type { Customer } from '../types'

// Helper for empty strings
const emptyIfNull = (val: string | undefined | null) => val || ''

interface CustomerOrder {
  id: number
  external_order_id: string
  external_order_number?: string
  order_date: string
  order_total_cents?: number
  currency_code?: string
  status_normalized?: string
  marketplace?: string
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null)

  const [formData, setFormData] = useState<Partial<Customer>>({})

  // Orders expansion state
  const [expandedCustomerId, setExpandedCustomerId] = useState<number | null>(null)
  const [customerOrders, setCustomerOrders] = useState<CustomerOrder[]>([])
  const [ordersLoading, setOrdersLoading] = useState(false)

  // Invoice modal state
  const [invoiceModalOpen, setInvoiceModalOpen] = useState(false)
  const [invoiceHtml, setInvoiceHtml] = useState('')
  const [invoiceLoading, setInvoiceLoading] = useState(false)

  // Admin key for invoice generation
  const [adminKey, setAdminKey] = useState('')

  const loadCustomers = async () => {
    const data = await customersApi.list()
    setCustomers(data)
  }

  useEffect(() => {
    loadCustomers()
  }, [])

  const handleSave = async () => {
    if (!formData.name) {
      alert('Name is required')
      return
    }

    try {
      if (editingCustomer) {
        await customersApi.update(editingCustomer.id, formData)
      } else {
        // For new customers, cast to any to bypass strict type check on create
        await customersApi.create(formData as any)
      }
      setDialogOpen(false)
      loadCustomers()
    } catch (err) {
      console.error(err)
      alert('Failed to save customer')
    }
  }

  const handleDelete = async (id: number) => {
    if (confirm('Are you sure you want to delete this customer?')) {
      await customersApi.delete(id)
      loadCustomers()
    }
  }

  const openAdd = () => {
    setEditingCustomer(null)
    setFormData({
      name: '',
      first_name: '',
      last_name: '',
      buyer_email: '',
      mobile_phone: '',
      work_phone: '',
      other_phone: '',
      billing_address1: '',
      billing_address2: '',
      billing_city: '',
      billing_state: '',
      billing_postal_code: '',
      billing_country: '',
      shipping_name: '',
      shipping_address1: '',
      shipping_address2: '',
      shipping_city: '',
      shipping_state: '',
      shipping_postal_code: '',
      shipping_country: '',
    })
    setDialogOpen(true)
  }

  const openEdit = (customer: Customer) => {
    setEditingCustomer(customer)
    setFormData({
      // Identity
      name: emptyIfNull(customer.name),
      first_name: emptyIfNull(customer.first_name),
      last_name: emptyIfNull(customer.last_name),
      buyer_email: emptyIfNull(customer.buyer_email),

      // Phones
      mobile_phone: emptyIfNull(customer.mobile_phone),
      work_phone: emptyIfNull(customer.work_phone),
      other_phone: emptyIfNull(customer.other_phone),

      // Legacy
      address: emptyIfNull(customer.address),
      phone: emptyIfNull(customer.phone),

      // Billing
      billing_address1: emptyIfNull(customer.billing_address1),
      billing_address2: emptyIfNull(customer.billing_address2),
      billing_city: emptyIfNull(customer.billing_city),
      billing_state: emptyIfNull(customer.billing_state),
      billing_postal_code: emptyIfNull(customer.billing_postal_code),
      billing_country: emptyIfNull(customer.billing_country),

      // Shipping
      shipping_name: emptyIfNull(customer.shipping_name),
      shipping_address1: emptyIfNull(customer.shipping_address1),
      shipping_address2: emptyIfNull(customer.shipping_address2),
      shipping_city: emptyIfNull(customer.shipping_city),
      shipping_state: emptyIfNull(customer.shipping_state),
      shipping_postal_code: emptyIfNull(customer.shipping_postal_code),
      shipping_country: emptyIfNull(customer.shipping_country),
    })
    setDialogOpen(true)
  }

  const handleChange = (field: keyof Customer, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  // Toggle orders expansion
  const handleToggleOrders = async (customerId: number) => {
    if (expandedCustomerId === customerId) {
      // Collapse
      setExpandedCustomerId(null)
      setCustomerOrders([])
    } else {
      // Expand and load orders
      setExpandedCustomerId(customerId)
      setOrdersLoading(true)
      setCustomerOrders([])

      try {
        const response = await fetch(`/api/marketplace-orders?customer_id=${customerId}&limit=50`)
        if (response.ok) {
          const orders: CustomerOrder[] = await response.json()
          setCustomerOrders(orders)
        }
      } catch (err) {
        console.error('Failed to fetch orders:', err)
      } finally {
        setOrdersLoading(false)
      }
    }
  }

  // Open invoice preview for a single order
  const handleOpenInvoice = async (orderId: number) => {
    if (!adminKey.trim()) {
      alert('Please enter Admin Key to view invoices')
      return
    }

    setInvoiceLoading(true)
    setInvoiceHtml('')
    setInvoiceModalOpen(true)

    try {
      const response = await fetch('/api/marketplace-orders/invoice', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Key': adminKey.trim()
        },
        body: JSON.stringify({
          order_ids: [orderId],
          mode: 'html'
        })
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(`Error ${response.status}: ${text.slice(0, 100)}`)
      }

      const data = await response.json()
      setInvoiceHtml(data.html)
    } catch (err) {
      setInvoiceHtml(`<p style="color:red;">Failed to load invoice: ${err instanceof Error ? err.message : 'Unknown error'}</p>`)
    } finally {
      setInvoiceLoading(false)
    }
  }

  const formatCurrency = (cents?: number, currency?: string) => {
    if (cents === null || cents === undefined) return '—'
    const dollars = cents / 100
    return `${currency || 'USD'} ${dollars.toFixed(2)}`
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString()
    } catch {
      return dateStr
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Customers</Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <TextField
            label="Admin Key"
            type="password"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            size="small"
            sx={{ width: 200 }}
            placeholder="For invoice preview"
          />
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={openAdd}
          >
            Add Customer
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Phone</TableCell>
              <TableCell>Location</TableCell>
              <TableCell>Source</TableCell>
              <TableCell>Orders</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {customers.map((customer) => (
              <>
                <TableRow key={customer.id}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">{customer.name}</Typography>
                    {(customer.first_name || customer.last_name) && (
                      <Typography variant="caption" color="text.secondary">
                        {customer.first_name} {customer.last_name}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {customer.buyer_email && (
                      <Box>{customer.buyer_email}</Box>
                    )}
                    {customer.marketplace_buyer_email && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        Proxy: {customer.marketplace_buyer_email}
                      </Typography>
                    )}
                    {!customer.buyer_email && !customer.marketplace_buyer_email && '-'}
                  </TableCell>
                  <TableCell>
                    {customer.mobile_phone || customer.phone || '-'}
                  </TableCell>
                  <TableCell>
                    {customer.shipping_city ? (
                      `${customer.shipping_city}, ${customer.shipping_state || ''}`
                    ) : (
                      customer.address || '-'
                    )}
                  </TableCell>
                  <TableCell>
                    {customer.source_marketplace ? (
                      <Chip
                        label={customer.source_marketplace}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    ) : '-'}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="small"
                      onClick={() => handleToggleOrders(customer.id)}
                      endIcon={expandedCustomerId === customer.id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    >
                      {expandedCustomerId === customer.id ? 'Hide' : 'View'}
                    </Button>
                  </TableCell>
                  <TableCell>
                    <IconButton onClick={() => openEdit(customer)}><EditIcon /></IconButton>
                    <IconButton onClick={() => handleDelete(customer.id)}><DeleteIcon /></IconButton>
                  </TableCell>
                </TableRow>
                {/* Orders expansion row */}
                <TableRow key={`${customer.id}-orders`}>
                  <TableCell colSpan={7} sx={{ py: 0, borderBottom: expandedCustomerId === customer.id ? undefined : 'none' }}>
                    <Collapse in={expandedCustomerId === customer.id} timeout="auto" unmountOnExit>
                      <Box sx={{ p: 2, bgcolor: 'grey.50' }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Orders for {customer.name}
                        </Typography>
                        {ordersLoading ? (
                          <CircularProgress size={20} />
                        ) : customerOrders.length === 0 ? (
                          <Typography variant="body2" color="text.secondary">No orders found</Typography>
                        ) : (
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                            {customerOrders.map((order) => (
                              <Chip
                                key={order.id}
                                icon={<ReceiptIcon />}
                                label={`#${order.external_order_number || order.external_order_id} • ${formatDate(order.order_date)} • ${formatCurrency(order.order_total_cents, order.currency_code)}`}
                                onClick={() => handleOpenInvoice(order.id)}
                                variant="outlined"
                                sx={{ cursor: 'pointer' }}
                              />
                            ))}
                          </Box>
                        )}
                      </Box>
                    </Collapse>
                  </TableCell>
                </TableRow>
              </>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Customer Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingCustomer ? 'Edit Customer' : 'Add Customer'}</DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={3}>
            {/* Identity Group */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Identity</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="Display Name" value={formData.name || ''} onChange={e => handleChange('name', e.target.value)} required />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="First Name" value={formData.first_name || ''} onChange={e => handleChange('first_name', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="Last Name" value={formData.last_name || ''} onChange={e => handleChange('last_name', e.target.value)} />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Buyer Email (Real)" value={formData.buyer_email || ''} onChange={e => handleChange('buyer_email', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={6}>
                  {editingCustomer && (
                    <TextField
                      fullWidth
                      label="Relay Email (Read-only)"
                      value={editingCustomer.marketplace_buyer_email || ''}
                      disabled
                      helperText="From Marketplace"
                    />
                  )}
                </Grid>
              </Grid>
            </Grid>

            <Grid item xs={12}><Divider /></Grid>

            {/* Phones Group */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Phones</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="Mobile" value={formData.mobile_phone || ''} onChange={e => handleChange('mobile_phone', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="Work" value={formData.work_phone || ''} onChange={e => handleChange('work_phone', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="Other" value={formData.other_phone || ''} onChange={e => handleChange('other_phone', e.target.value)} />
                </Grid>
              </Grid>
            </Grid>

            <Grid item xs={12}><Divider /></Grid>

            {/* Shipping Address */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Shipping Address</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField fullWidth label="Shipping Name" value={formData.shipping_name || ''} onChange={e => handleChange('shipping_name', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Line 1" value={formData.shipping_address1 || ''} onChange={e => handleChange('shipping_address1', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Line 2" value={formData.shipping_address2 || ''} onChange={e => handleChange('shipping_address2', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="City" value={formData.shipping_city || ''} onChange={e => handleChange('shipping_city', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="State" value={formData.shipping_state || ''} onChange={e => handleChange('shipping_state', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="Postal Code" value={formData.shipping_postal_code || ''} onChange={e => handleChange('shipping_postal_code', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Country" value={formData.shipping_country || ''} onChange={e => handleChange('shipping_country', e.target.value)} />
                </Grid>
              </Grid>
            </Grid>

            <Grid item xs={12}><Divider /></Grid>

            {/* Billing Address */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Billing Address</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Line 1" value={formData.billing_address1 || ''} onChange={e => handleChange('billing_address1', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Line 2" value={formData.billing_address2 || ''} onChange={e => handleChange('billing_address2', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="City" value={formData.billing_city || ''} onChange={e => handleChange('billing_city', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="State" value={formData.billing_state || ''} onChange={e => handleChange('billing_state', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="Postal Code" value={formData.billing_postal_code || ''} onChange={e => handleChange('billing_postal_code', e.target.value)} />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Country" value={formData.billing_country || ''} onChange={e => handleChange('billing_country', e.target.value)} />
                </Grid>
              </Grid>
            </Grid>

            {editingCustomer && editingCustomer.source_marketplace && (
              <>
                <Grid item xs={12}><Divider /></Grid>
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">
                    Linked to {editingCustomer.source_marketplace} (ID: {editingCustomer.source_customer_id || 'N/A'})
                  </Typography>
                </Grid>
              </>
            )}

          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>

      {/* Invoice Preview Modal */}
      <Dialog open={invoiceModalOpen} onClose={() => setInvoiceModalOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Invoice Preview</DialogTitle>
        <DialogContent>
          {invoiceLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Box
              sx={{ minHeight: 400 }}
              dangerouslySetInnerHTML={{ __html: invoiceHtml }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInvoiceModalOpen(false)}>Close</Button>
          <Button
            variant="contained"
            onClick={() => {
              // Open in new window for printing
              const printWindow = window.open('', '_blank')
              if (printWindow) {
                printWindow.document.write(invoiceHtml)
                printWindow.document.close()
              }
            }}
            disabled={!invoiceHtml || invoiceLoading}
          >
            Open in New Tab
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
