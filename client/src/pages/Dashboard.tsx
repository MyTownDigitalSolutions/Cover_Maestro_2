import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Grid, Paper, Typography, Box, Button } from '@mui/material'
import BusinessIcon from '@mui/icons-material/Business'
import CategoryIcon from '@mui/icons-material/Category'
import TextureIcon from '@mui/icons-material/Texture'
import PeopleIcon from '@mui/icons-material/People'
import { manufacturersApi, modelsApi, materialsApi, customersApi } from '../services/api'

interface StatCardProps {
  title: string
  value: number
  icon: React.ReactNode
  color: string
}

function StatCard({ title, value, icon, color }: StatCardProps) {
  return (
    <Paper sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
      <Box sx={{ bgcolor: color, p: 2, borderRadius: 2, color: 'white' }}>
        {icon}
      </Box>
      <Box>
        <Typography variant="h4">{value}</Typography>
        <Typography color="text.secondary">{title}</Typography>
      </Box>
    </Paper>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState({
    manufacturers: 0,
    models: 0,
    materials: 0,
    customers: 0
  })

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [manufacturers, models, materials, customers] = await Promise.all([
          manufacturersApi.list(),
          modelsApi.list(),
          materialsApi.list(),
          customersApi.list()
        ])
        setStats({
          manufacturers: manufacturers.length,
          models: models.length,
          materials: materials.length,
          customers: customers.length
        })
      } catch (error) {
        console.error('Failed to load stats:', error)
      }
    }
    loadStats()
  }, [])

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Manufacturers"
            value={stats.manufacturers}
            icon={<BusinessIcon />}
            color="#1976d2"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Models"
            value={stats.models}
            icon={<CategoryIcon />}
            color="#388e3c"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Materials"
            value={stats.materials}
            icon={<TextureIcon />}
            color="#f57c00"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Customers"
            value={stats.customers}
            icon={<PeopleIcon />}
            color="#7b1fa2"
          />
        </Grid>
      </Grid>
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Welcome to Cover Making Application
        </Typography>
        <Typography color="text.secondary" paragraph>
          Manage custom fabric covers for musical instruments, calculate prices,
          and generate marketplace listing templates. Use the navigation menu to
          access different sections of the application.
        </Typography>
        <Button
          variant="contained"
          onClick={() => navigate('/product-catalog')}
        >
          Go to Product Catalog Creation
        </Button>
      </Paper>
    </Box>
  )
}
