import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Table, Column } from '@/components/common/Table'

interface RowData {
  id: string
  name: string
  status: string
}

describe('Table Component', () => {
  const columns: Column<RowData>[] = [
    { header: 'Service Name', accessor: 'name' },
    { header: 'Status', accessor: (r) => <span className="font-bold">{r.status}</span> },
  ]

  const data: RowData[] = [
    { id: '1', name: 'checkout-api', status: 'HEALTHY' },
    { id: '2', name: 'payment-gateway', status: 'UNHEALTHY' },
  ]

  it('renders table headers and rows correctly', () => {
    render(<Table columns={columns} data={data} keyExtractor={(r) => r.id} />)
    expect(screen.getByText('Service Name')).toBeInTheDocument()
    expect(screen.getByText('checkout-api')).toBeInTheDocument()
    expect(screen.getByText('payment-gateway')).toBeInTheDocument()
  })

  it('displays empty message when no rows are present', () => {
    render(
      <Table
        columns={columns}
        data={[]}
        keyExtractor={(r) => r.id}
        emptyMessage="No microservices registered"
      />
    )
    expect(screen.getByText('No microservices registered')).toBeInTheDocument()
  })

  it('triggers onRowClick when row is clicked', () => {
    const handleRowClick = vi.fn()
    render(
      <Table
        columns={columns}
        data={data}
        keyExtractor={(r) => r.id}
        onRowClick={handleRowClick}
      />
    )
    fireEvent.click(screen.getByText('checkout-api'))
    expect(handleRowClick).toHaveBeenCalledWith(data[0])
  })
})

