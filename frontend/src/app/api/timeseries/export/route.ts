import { NextRequest, NextResponse } from 'next/server';
import { Client } from 'pg';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;

  // Parse query parameters
  const start = searchParams.get('start'); // ISO 8601 timestamp
  const end = searchParams.get('end');
  const haystackName = searchParams.get('haystackName'); // Optional filter
  const format = searchParams.get('format') || 'csv'; // csv or json

  if (!start || !end) {
    return NextResponse.json(
      { error: 'Missing required parameters: start, end' },
      { status: 400 }
    );
  }

  try {
    // Connect to TimescaleDB
    const client = new Client({
      host: process.env.TIMESCALEDB_HOST || 'localhost',
      port: parseInt(process.env.TIMESCALEDB_PORT || '5432'),
      database: process.env.TIMESCALEDB_DB || 'timescaledb',
      user: process.env.TIMESCALEDB_USER || 'anatoli',
      password: process.env.TIMESCALEDB_PASSWORD || '',
    });

    await client.connect();

    // Build query
    let query = `
      SELECT
        time,
        haystack_name,
        dis,
        value,
        units,
        quality,
        device_name,
        device_ip,
        object_type,
        object_instance
      FROM sensor_readings
      WHERE time >= $1 AND time <= $2
    `;

    const params: any[] = [start, end];

    if (haystackName) {
      query += ` AND haystack_name = $3`;
      params.push(haystackName);
    }

    query += ` ORDER BY time DESC LIMIT 10000`; // Safety limit

    // Execute query
    const result = await client.query(query, params);
    await client.end();

    if (format === 'json') {
      const jsonContent = JSON.stringify(result.rows, null, 2);
      return new NextResponse(jsonContent, {
        headers: {
          'Content-Type': 'application/json',
          'Content-Disposition': `attachment; filename="sensor_data_${start}_${end}.json"`,
        },
      });
    }

    // Handle empty results
    if (result.rows.length === 0) {
      return NextResponse.json(
        {
          error: 'No data found for the selected time range',
          hint: 'Data is collected when MQTT-enabled points are being polled. Please ensure: 1) BACnet discovery has been run, 2) Points have MQTT publishing enabled, 3) Sufficient time has passed for data collection.'
        },
        { status: 404 }
      );
    }

    // Convert to CSV

    const headers = Object.keys(result.rows[0]);
    const csvLines = [
      headers.join(','), // Header row
      ...result.rows.map(row =>
        headers.map(h => {
          const value = row[h];
          // Escape commas and quotes
          if (value === null) return '';
          const strValue = String(value);
          if (strValue.includes(',') || strValue.includes('"') || strValue.includes('\n')) {
            return `"${strValue.replace(/"/g, '""')}"`;
          }
          return strValue;
        }).join(',')
      )
    ];

    const csv = csvLines.join('\n');

    return new NextResponse(csv, {
      headers: {
        'Content-Type': 'text/csv',
        'Content-Disposition': `attachment; filename="sensor_data_${start}_${end}.csv"`,
      },
    });

  } catch (error) {
    console.error('Export error:', error);
    return NextResponse.json(
      { error: 'Export failed', details: String(error) },
      { status: 500 }
    );
  }
}
