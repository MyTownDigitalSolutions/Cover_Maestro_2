import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Box, Drawer, AppBar, Toolbar, Typography, List, ListItem,
  ListItemButton, ListItemIcon, ListItemText, Divider, IconButton, Collapse, Button
} from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import DashboardIcon from '@mui/icons-material/Dashboard'
import BusinessIcon from '@mui/icons-material/Business'
import CategoryIcon from '@mui/icons-material/Category'
import TextureIcon from '@mui/icons-material/Texture'
import BuildIcon from '@mui/icons-material/Build'
import InventoryIcon from '@mui/icons-material/Inventory'
import LocalOfferIcon from '@mui/icons-material/LocalOffer'
import DesignServicesIcon from '@mui/icons-material/DesignServices'
import LocalShippingIcon from '@mui/icons-material/LocalShipping'
import PeopleIcon from '@mui/icons-material/People'
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart'
import CalculateIcon from '@mui/icons-material/Calculate'
import DescriptionIcon from '@mui/icons-material/Description'
import FileDownloadIcon from '@mui/icons-material/FileDownload'
import SettingsIcon from '@mui/icons-material/Settings'
import AttachMoneyIcon from '@mui/icons-material/AttachMoney'
import MenuBookIcon from '@mui/icons-material/MenuBook'
import StorefrontIcon from '@mui/icons-material/Storefront'
import VpnKeyIcon from '@mui/icons-material/VpnKey'
import ListAltIcon from '@mui/icons-material/ListAlt'
import ExpandLess from '@mui/icons-material/ExpandLess'
import ExpandMore from '@mui/icons-material/ExpandMore'

/*
 * UI WORK LOG - 2025-12-24
 * -------------------------
 * - Implemented Sidebar Navigation Restructuring:
 *   - Created "Pricing / Calculation Settings" collapsible group.
 *   - Created "Suppliers / Materials" collapsible group.
 *   - Removed root-level items for cleanup.
 * - Implemented Hub Pages:
 *   - Created PricingCalculationSettingsPage (Hub for Pricing).
 *   - Created SuppliersMaterialsPage (Hub for Suppliers/Materials).
 * - Implemented Deep Linking:
 *   - Added "Material Role Assignments" section to Materials Page (embedding existing Settings UI).
 *   - Added deep-link anchor (#material-roles) with auto-scroll.
 *   - Updated Hub Page to link directly to this anchor.
 *
 * This comment serves as the authoritative record of changes due to task numbering drift.
 */

const drawerWidth = 240

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
  {
    text: 'Product Catalog Creation',
    icon: <MenuBookIcon />,
    path: '/product-catalog',
    children: [
      { text: 'Manufacturers', icon: <BusinessIcon />, path: '/manufacturers' },
      { text: 'Models', icon: <CategoryIcon />, path: '/models' },
      { text: 'Equipment Types', icon: <BuildIcon />, path: '/equipment-types' },
      { text: 'Product Design Options', icon: <DesignServicesIcon />, path: '/design-options' },
    ]
  },
  {
    text: 'Global Settings',
    icon: <SettingsIcon />,
    path: '/settings/pricing/labor',
    children: [
      {
        text: 'Pricing',
        icon: <CalculateIcon />,
        path: '/settings/pricing/labor',
        children: [
          { text: 'Pricing Options', icon: <LocalOfferIcon />, path: '/pricing-options' },
          { text: 'Pricing Calculator', icon: <CalculateIcon />, path: '/pricing' },
          { text: 'Labor Settings', icon: <SettingsIcon />, path: '/settings/pricing/labor' },
          { text: 'Variant Profits', icon: <AttachMoneyIcon />, path: '/settings/pricing/profits' },
        ]
      },
      {
        text: 'Shipping',
        icon: <LocalShippingIcon />,
        path: '/settings/shipping-config',
        children: [
          { text: 'Shipping Rates', icon: <AttachMoneyIcon />, path: '/settings/shipping-rates' },
          { text: 'Shipping Defaults', icon: <LocalShippingIcon />, path: '/settings/shipping-defaults' },
          { text: 'Shipping Config', icon: <SettingsIcon />, path: '/settings/shipping-config' },
        ]
      },
      {
        text: 'Materials',
        icon: <TextureIcon />,
        path: '/settings/material-role-assignments',
        children: [
          { text: 'Material Role Assignments', icon: <SettingsIcon />, path: '/settings/material-role-assignments' },
          { text: 'Material Role Configs', icon: <SettingsIcon />, path: '/settings/material-role-configs' },
          { text: 'Global Colors', icon: <TextureIcon />, path: '/settings/material-colors' },
        ]
      },
      {
        text: 'Marketplace Settings',
        icon: <StorefrontIcon />,
        path: '/settings/marketplace/fees',
        children: [
          { text: 'Marketplace Fee Rates', icon: <AttachMoneyIcon />, path: '/settings/marketplace/fees' },
          { text: 'eBay Store Category Hierarchy', icon: <StorefrontIcon />, path: '/settings/marketplace/ebay-store-category-hierarchy' },
        ]
      },
    ]
  },
  {
    text: 'Suppliers / Materials',
    icon: <InventoryIcon />,
    path: '/suppliers-materials',
    children: [
      { text: 'Materials', icon: <TextureIcon />, path: '/materials' },
      { text: 'Suppliers', icon: <LocalShippingIcon />, path: '/suppliers' },
    ]
  },
  { text: 'Customers', icon: <PeopleIcon />, path: '/customers' },
  { text: 'Orders', icon: <ShoppingCartIcon />, path: '/orders' },
  {
    text: 'Templates',
    icon: <DescriptionIcon />,
    path: '/templates/amazon', // Default to Amazon
    children: [
      { text: 'Amazon', icon: <DescriptionIcon />, path: '/templates/amazon' },
      { text: 'eBay', icon: <DescriptionIcon />, path: '/templates/ebay' },
      { text: 'Reverb', icon: <DescriptionIcon />, path: '/templates/reverb' },
      { text: 'Etsy', icon: <DescriptionIcon />, path: '/templates/etsy' },
    ]
  },
  {
    text: 'Export',
    icon: <FileDownloadIcon />,
    path: '/export/general',
    children: [
      { text: 'General', icon: <FileDownloadIcon />, path: '/export/general' },
      { text: 'Amazon', icon: <FileDownloadIcon />, path: '/export/amazon' },
      { text: 'eBay', icon: <FileDownloadIcon />, path: '/export/ebay' },
      { text: 'Etsy', icon: <FileDownloadIcon />, path: '/export/etsy' },
      { text: 'Reverb', icon: <FileDownloadIcon />, path: '/export/reverb' },
    ]
  },
  {
    text: 'Marketplaces',
    icon: <StorefrontIcon />,
    path: '/marketplaces/credentials', // Default to Credentials
    children: [
      { text: 'Marketplace Credentials', icon: <VpnKeyIcon />, path: '/marketplaces/credentials' },
      { text: 'Marketplace Orders', icon: <ListAltIcon />, path: '/marketplaces/orders' },
    ]
  },
]

interface LayoutProps {
  children: React.ReactNode
  onSignOut?: () => void
}

export default function Layout({ children, onSignOut }: LayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const [openSections, setOpenSections] = useState<Record<string, boolean>>({})

  useEffect(() => {
    const newOpen: Record<string, boolean> = {}
    const collectOpenKeys = (items: any[], parentKey = ''): boolean => {
      let foundInBranch = false
      items.forEach((item) => {
        const itemKey = parentKey ? `${parentKey}__${item.text}` : item.text
        const directMatch = item.path ? isPathSelected(item.path) : false
        const childMatch = item.children ? collectOpenKeys(item.children, itemKey) : false
        if ((directMatch || childMatch) && item.children) {
          newOpen[itemKey] = true
        }
        if (directMatch || childMatch) {
          foundInBranch = true
        }
      })
      return foundInBranch
    }

    // Check Product Catalog
    if (['/product-catalog', '/manufacturers', '/models', '/equipment-types', '/design-options'].some(p => location.pathname.startsWith(p))) {
      newOpen['Product Catalog Creation'] = true
    }

    collectOpenKeys(menuItems)

    if (Object.keys(newOpen).length > 0) {
      setOpenSections(prev => ({ ...prev, ...newOpen }))
    }
  }, [location.pathname])

  const handleExpandClick = (e: React.MouseEvent, key: string) => {
    e.stopPropagation()
    setOpenSections(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const isPathSelected = (targetPath: string) => {
    const [pathname, query] = targetPath.split('?')
    if (location.pathname !== pathname) return false
    if (!query) return true
    return location.search === `?${query}`
  }

  const renderMenuItems = (items: any[], depth = 0, parentKey = '') => {
    return items.map((item: any) => {
      const itemKey = parentKey ? `${parentKey}__${item.text}` : item.text
      if (item.children) {
        return (
          <div key={itemKey}>
            <ListItem disablePadding>
              <ListItemButton
                selected={isPathSelected(item.path)}
                onClick={() => item.path && navigate(item.path)}
                sx={{ pl: 2 + depth * 2 }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
                <IconButton onClick={(e) => handleExpandClick(e, itemKey)} edge="end" size="small">
                  {openSections[itemKey] ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              </ListItemButton>
            </ListItem>
            <Collapse in={!!openSections[itemKey]} timeout="auto" unmountOnExit>
              <List component="div" disablePadding>
                {renderMenuItems(item.children, depth + 1, itemKey)}
              </List>
            </Collapse>
          </div>
        )
      }
      return (
        <ListItem key={itemKey} disablePadding>
          <ListItemButton
            selected={isPathSelected(item.path)}
            onClick={() => navigate(item.path)}
            sx={{ pl: 2 + depth * 2 }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItemButton>
        </ListItem>
      )
    })
  }

  const drawer = (
    <div>
      <Toolbar>
        <Typography variant="h6" noWrap>
          Cover Maker
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {renderMenuItems(menuItems)}
      </List>
    </div>
  )


  return (
    <Box sx={{ display: 'flex', width: '100%' }}>
      <AppBar
        position="fixed"
        sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={() => setMobileOpen(!mobileOpen)}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div">
            Cover Making Application
          </Typography>
          <Box sx={{ ml: 'auto' }}>
            <Button color="inherit" onClick={onSignOut}>Sign Out</Button>
          </Box>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          display: { xs: 'none', sm: 'block' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
        }}
      >
        {drawer}
      </Drawer>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: 8
        }}
      >
        {children}
      </Box>
    </Box>
  )
}
