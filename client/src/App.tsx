import { useEffect, useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Navigate } from 'react-router-dom'
import { Box, CircularProgress } from '@mui/material'
import type { Session } from '@supabase/supabase-js'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import Dashboard from './pages/Dashboard'
import ProductCatalogCreationPage from './pages/ProductCatalogCreationPage'
import PricingCalculationSettingsPage from './pages/PricingCalculationSettingsPage'
import SuppliersMaterialsPage from './pages/SuppliersMaterialsPage'
import ManufacturersPage from './pages/ManufacturersPage'
import ModelsPage from './pages/ModelsPage'
import MaterialsPage from './pages/MaterialsPage'
import SuppliersPage from './pages/SuppliersPage'
import EquipmentTypesPage from './pages/EquipmentTypesPage'
import PricingOptionsPage from './pages/PricingOptionsPage'
import DesignOptionsPage from './pages/DesignOptionsPage'
import CustomersPage from './pages/CustomersPage'
import OrdersPage from './pages/OrdersPage'
import PricingCalculator from './pages/PricingCalculator'

import AmazonTemplatesPage from './pages/AmazonTemplatesPage'
import EbayTemplatesPage from './pages/EbayTemplatesPage'
import ReverbTemplatesPage from './pages/ReverbTemplatesPage'
import EtsyTemplatesPage from './pages/EtsyTemplatesPage'
import AmazonExportPage from './pages/AmazonExportPage' // Amazon Export (keeping existing file)
import EbayExportPage from './pages/EbayExportPage'
import ReverbExportPage from './pages/ReverbExportPage'
import EtsyExportPage from './pages/EtsyExportPage'
import GeneralExportPage from './pages/GeneralExportPage'
import SettingsPage from './pages/SettingsPage'
import ShippingRatesPage from './pages/ShippingRatesPage'
import ShippingDefaultsPage from './pages/ShippingDefaultsPage'
import MaterialRoleConfigsPage from './pages/MaterialRoleConfigsPage'
import MaterialRoleAssignmentsPage from './pages/MaterialRoleAssignmentsPage'
import GlobalColorsPage from './pages/GlobalColorsPage'
import SettingsPricingLaborPage from './pages/SettingsPricingLaborPage'
import SettingsPricingProfitsPage from './pages/SettingsPricingProfitsPage'
import SettingsMarketplaceFeesPage from './pages/SettingsMarketplaceFeesPage'
import SettingsShippingConfigPage from './pages/SettingsShippingConfigPage'
import MarketplaceCredentialsPage from './pages/MarketplaceCredentialsPage'
import MarketplaceOrdersPage from './pages/MarketplaceOrdersPage'
import EbayStoreCategoryHierarchyPage from './pages/EbayStoreCategoryHierarchyPage'
import { setAccessToken, supabase } from './auth/supabase'

function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [authLoading, setAuthLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return
      const currentSession = data.session ?? null
      setSession(currentSession)
      setAccessToken(currentSession?.access_token ?? null)
      setAuthLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setAccessToken(nextSession?.access_token ?? null)
      setAuthLoading(false)
    })

    return () => {
      mounted = false
      subscription.unsubscribe()
    }
  }, [])

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    setSession(null)
    setAccessToken(null)
  }

  if (authLoading) {
    return (
      <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!session) {
    return <LoginPage onLoggedIn={() => undefined} />
  }

  return (
    <Box sx={{ display: 'flex' }}>
      <Layout onSignOut={handleSignOut}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/product-catalog" element={<ProductCatalogCreationPage />} />
          <Route path="/pricing-settings" element={<PricingCalculationSettingsPage />} />
          <Route path="/suppliers-materials" element={<SuppliersMaterialsPage />} />
          <Route path="/manufacturers" element={<ManufacturersPage />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/materials" element={<MaterialsPage />} />
          <Route path="/suppliers" element={<SuppliersPage />} />
          <Route path="/equipment-types" element={<EquipmentTypesPage />} />
          <Route path="/pricing-options" element={<PricingOptionsPage />} />
          <Route path="/design-options" element={<DesignOptionsPage />} />
          <Route path="/customers" element={<CustomersPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/pricing" element={<PricingCalculator />} />
          <Route path="/templates/amazon" element={<AmazonTemplatesPage />} />
          <Route path="/templates/ebay" element={<EbayTemplatesPage />} />
          <Route path="/templates/reverb" element={<ReverbTemplatesPage />} />
          <Route path="/templates/etsy" element={<EtsyTemplatesPage />} />
          <Route path="/export/amazon" element={<AmazonExportPage />} />
          <Route path="/export/ebay" element={<EbayExportPage />} />
          <Route path="/export/reverb" element={<ReverbExportPage />} />
          <Route path="/export/etsy" element={<EtsyExportPage />} />
          <Route path="/export/general" element={<GeneralExportPage />} />
          <Route path="/export" element={<GeneralExportPage />} />
          <Route path="/settings" element={<Navigate to="/settings/pricing/labor" replace />} />
          <Route path="/settings/legacy" element={<SettingsPage />} />
          <Route path="/settings/pricing/labor" element={<SettingsPricingLaborPage />} />
          <Route path="/settings/pricing/profits" element={<SettingsPricingProfitsPage />} />
          <Route path="/settings/marketplace/fees" element={<SettingsMarketplaceFeesPage />} />
          <Route path="/settings/marketplace/ebay-store-category-hierarchy" element={<EbayStoreCategoryHierarchyPage />} />
          <Route path="/settings/shipping-config" element={<SettingsShippingConfigPage />} />
          <Route path="/settings/shipping-rates" element={<ShippingRatesPage />} />
          <Route path="/settings/shipping-defaults" element={<ShippingDefaultsPage />} />
          <Route path="/settings/material-role-configs" element={<MaterialRoleConfigsPage />} />
          <Route path="/settings/material-role-assignments" element={<MaterialRoleAssignmentsPage />} />
          <Route path="/settings/material-colors" element={<GlobalColorsPage />} />
          <Route path="/marketplaces/credentials" element={<MarketplaceCredentialsPage />} />
          <Route path="/marketplaces/orders" element={<MarketplaceOrdersPage />} />
        </Routes>
      </Layout>
    </Box>
  )
}

export default App
