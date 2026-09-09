-- =============================================================================
-- POS-AI — DDL del esquema `system_pos`
-- =============================================================================
--
-- FUENTE DE VERDAD del esquema de la DB del POS.
-- Ante cualquier discrepancia entre este archivo y el resumen de CLAUDE.md,
-- manda ESTE archivo. El resumen puede quedar desactualizado; el DDL no.
--
-- Origen:     DB del POS (PostgreSQL / Supabase), esquema `system_pos`
-- Exportado:  2026-09-08          <-- ACTUALIZAR en cada re-exportación
-- Schema ver: (opcional: tag/migración del POS al momento de exportar)
--
-- -----------------------------------------------------------------------------
-- Cómo usarlo
-- -----------------------------------------------------------------------------
-- Este microservicio NO ejecuta este script: es READ-ONLY sobre las tablas
-- operacionales del POS y solo escribe en las 4 tablas IA. El archivo existe
-- para verificar nombres reales de tablas y columnas ANTES de escribir queries.
--
-- Verificar contra este DDL siempre que:
--   * se escriba un extractor nuevo en app/etl/extractors/
--   * se agregue una consulta en app/analytics/
--   * una query falle por columna inexistente
--
-- Trampas ya conocidas (ver CLAUDE.md § Notas Importantes):
--   * `movimiento_financiero` NO existe        -> usar `gasto` / `movimiento_caja`
--   * `producto.fecha_vencimiento` NO existe   -> está en `inventario`
--   * `producto.es_perecedero` NO existe       -> inventario.fecha_vencimiento IS NOT NULL
--   * `producto.stock_actual` NO existe        -> está en `inventario`
--   * `proveedor.nombre` NO existe             -> es `razon_social`
--   * `detalle_compra.precio_unitario` NO existe -> es `costo_unitario`
--   * emails: la columna es `correo`, nunca `email`
--   * PKs: `id_<tabla>` (id_venta, id_producto), nunca `id` genérico
--
-- -----------------------------------------------------------------------------
-- Cómo re-exportarlo
-- -----------------------------------------------------------------------------
--   pg_dump --schema-only --schema=system_pos "<POS_DATABASE_URL>" > db/POS-AI-scriptdb.sql
--
-- Al re-exportar: actualizar la fecha de arriba y volver a pegar este encabezado,
-- que pg_dump no lo conserva.
--
-- =============================================================================


-- ▼▼▼ PEGAR AQUÍ EL DDL COMPLETO ▼▼▼
-- system_pos.empresa definition

-- Drop table

-- DROP TABLE system_pos.empresa;

CREATE TABLE system_pos.empresa (
	id_empresa bigserial NOT NULL,
	nombre varchar(150) NOT NULL,
	nit varchar(30) NULL,
	correo varchar(150) NULL,
	telefono varchar(20) NULL,
	direccion varchar(200) NULL,
	sector_economico varchar(120) NULL,
	estado bool DEFAULT true NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT empresa_pkey PRIMARY KEY (id_empresa),
	CONSTRAINT uq_empresa_nit UNIQUE (nit)
);


-- system_pos.metodo_pago definition

-- Drop table

-- DROP TABLE system_pos.metodo_pago;

CREATE TABLE system_pos.metodo_pago (
	id_metodo_pago bigserial NOT NULL,
	nombre varchar(50) NOT NULL,
	estado bool DEFAULT true NOT NULL,
	descripcion varchar(200) NULL,
	afecta_caja bool DEFAULT false NOT NULL,
	CONSTRAINT metodo_pago_nombre_key UNIQUE (nombre),
	CONSTRAINT metodo_pago_pkey PRIMARY KEY (id_metodo_pago)
);


-- system_pos.notification_event_type definition

-- Drop table

-- DROP TABLE system_pos.notification_event_type;

CREATE TABLE system_pos.notification_event_type (
	id_event_type bigserial NOT NULL,
	code varchar(80) NOT NULL,
	"name" varchar(120) NOT NULL,
	default_severity varchar(30) DEFAULT 'info'::character varying NOT NULL,
	enabled bool DEFAULT true NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	description varchar(250) NULL,
	CONSTRAINT chk_notification_event_severity CHECK (((default_severity)::text = ANY (ARRAY[('info'::character varying)::text, ('success'::character varying)::text, ('warning'::character varying)::text, ('error'::character varying)::text, ('critical'::character varying)::text]))),
	CONSTRAINT notification_event_type_code_key UNIQUE (code),
	CONSTRAINT notification_event_type_pkey PRIMARY KEY (id_event_type)
);


-- system_pos.permiso definition

-- Drop table

-- DROP TABLE system_pos.permiso;

CREATE TABLE system_pos.permiso (
	id_permiso bigserial NOT NULL,
	codigo varchar(100) NOT NULL,
	nombre varchar(120) NOT NULL,
	descripcion text NULL,
	estado bool DEFAULT true NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz NULL,
	CONSTRAINT permiso_codigo_key UNIQUE (codigo),
	CONSTRAINT permiso_pkey PRIMARY KEY (id_permiso)
);


-- system_pos.pgmigrations definition

-- Drop table

-- DROP TABLE system_pos.pgmigrations;

CREATE TABLE system_pos.pgmigrations (
	id serial4 NOT NULL,
	"name" varchar(255) NOT NULL,
	run_on timestamp NOT NULL,
	CONSTRAINT pgmigrations_pkey PRIMARY KEY (id)
);


-- system_pos.producto_sku_migration_backup definition

-- Drop table

-- DROP TABLE system_pos.producto_sku_migration_backup;

CREATE TABLE system_pos.producto_sku_migration_backup (
	id_producto int8 NOT NULL,
	id_empresa int8 NOT NULL,
	legacy_codigo_barras varchar(80) NULL,
	backed_up_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT producto_sku_migration_backup_pkey PRIMARY KEY (id_producto)
);


-- system_pos.rol definition

-- Drop table

-- DROP TABLE system_pos.rol;

CREATE TABLE system_pos.rol (
	id_rol bigserial NOT NULL,
	codigo varchar(50) NOT NULL,
	nombre varchar(100) NOT NULL,
	descripcion text NULL,
	estado bool DEFAULT true NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz NULL,
	CONSTRAINT rol_codigo_key UNIQUE (codigo),
	CONSTRAINT rol_pkey PRIMARY KEY (id_rol)
);


-- system_pos.ai_report_insert_failures definition

-- Drop table

-- DROP TABLE system_pos.ai_report_insert_failures;

CREATE TABLE system_pos.ai_report_insert_failures (
	id_ai_report_insert_failure bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	source_report_id varchar(120) NULL,
	payload jsonb NOT NULL,
	error_message text NOT NULL,
	attempts int4 DEFAULT 1 NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	resolved_at timestamptz NULL,
	CONSTRAINT ai_report_insert_failures_pkey PRIMARY KEY (id_ai_report_insert_failure),
	CONSTRAINT fk_ai_report_insert_failures_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_ai_report_insert_failures_pending ON system_pos.ai_report_insert_failures USING btree (id_empresa, created_at DESC) WHERE (resolved_at IS NULL);


-- system_pos.ai_reports definition

-- Drop table

-- DROP TABLE system_pos.ai_reports;

CREATE TABLE system_pos.ai_reports (
	id_ai_report bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	source_report_id varchar(120) NULL,
	period_start date NOT NULL,
	period_end date NOT NULL,
	generated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	prompt_version varchar(80) NULL,
	status varchar(30) DEFAULT 'completed'::character varying NOT NULL,
	summary text NULL,
	raw_output jsonb DEFAULT '{}'::jsonb NOT NULL,
	parsed_sections jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT ai_reports_pkey PRIMARY KEY (id_ai_report),
	CONSTRAINT chk_ai_reports_period CHECK ((period_end >= period_start)),
	CONSTRAINT chk_ai_reports_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'completed'::character varying, 'failed'::character varying])::text[]))),
	CONSTRAINT fk_ai_reports_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_ai_reports_tenant_generated ON system_pos.ai_reports USING btree (id_empresa, generated_at DESC, id_ai_report DESC);
CREATE INDEX idx_ai_reports_tenant_status ON system_pos.ai_reports USING btree (id_empresa, status, generated_at DESC);
CREATE UNIQUE INDEX uq_ai_reports_source_tenant ON system_pos.ai_reports USING btree (id_empresa, source_report_id) WHERE (source_report_id IS NOT NULL);


-- system_pos.categoria definition

-- Drop table

-- DROP TABLE system_pos.categoria;

CREATE TABLE system_pos.categoria (
	id_categoria bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	nombre varchar(100) NOT NULL,
	descripcion varchar(250) NULL,
	estado bool DEFAULT true NOT NULL,
	color varchar(20) DEFAULT '#64748b'::character varying NOT NULL,
	icono varchar(40) DEFAULT 'circle'::character varying NOT NULL,
	CONSTRAINT categoria_nombre_key UNIQUE (nombre),
	CONSTRAINT categoria_pkey PRIMARY KEY (id_categoria),
	CONSTRAINT fk_categoria_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_categoria_empresa_estado ON system_pos.categoria USING btree (id_empresa, estado);


-- system_pos.categoria_gasto definition

-- Drop table

-- DROP TABLE system_pos.categoria_gasto;

CREATE TABLE system_pos.categoria_gasto (
	id_categoria_gasto bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	nombre varchar(100) NOT NULL,
	descripcion varchar(250) NULL,
	estado bool DEFAULT true NOT NULL,
	tipo varchar(30) DEFAULT 'otro'::character varying NOT NULL,
	color varchar(20) DEFAULT '#64748b'::character varying NOT NULL,
	icono varchar(80) DEFAULT 'Receipt'::character varying NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	codigo varchar(40) NULL,
	CONSTRAINT categoria_gasto_pkey PRIMARY KEY (id_categoria_gasto),
	CONSTRAINT chk_categoria_gasto_tipo CHECK (((tipo)::text = ANY ((ARRAY['mercancia'::character varying, 'servicio'::character varying, 'impuesto'::character varying, 'otro'::character varying])::text[]))),
	CONSTRAINT uq_categoria_gasto_empresa_id UNIQUE (id_empresa, id_categoria_gasto),
	CONSTRAINT uq_categoria_gasto_nombre UNIQUE (id_empresa, nombre),
	CONSTRAINT fk_categoria_gasto_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_categoria_gasto_empresa_tipo ON system_pos.categoria_gasto USING btree (id_empresa, tipo) WHERE (estado = true);
CREATE UNIQUE INDEX uq_categoria_gasto_empresa_codigo ON system_pos.categoria_gasto USING btree (id_empresa, codigo) WHERE (codigo IS NOT NULL);


-- system_pos.cliente definition

-- Drop table

-- DROP TABLE system_pos.cliente;

CREATE TABLE system_pos.cliente (
	id_cliente bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	nombre varchar(100) NOT NULL,
	apellido varchar(100) NULL,
	tipo_documento varchar(20) NULL,
	numero_documento varchar(30) NULL,
	correo varchar(150) NULL,
	telefono varchar(20) NULL,
	direccion varchar(200) NULL,
	estado bool DEFAULT true NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	nota varchar(200) NULL,
	fecha_registro timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT cliente_numero_documento_key UNIQUE (numero_documento),
	CONSTRAINT cliente_pkey PRIMARY KEY (id_cliente),
	CONSTRAINT uq_cliente_empresa_id UNIQUE (id_empresa, id_cliente),
	CONSTRAINT fk_cliente_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_cliente_empresa_estado_nombre ON system_pos.cliente USING btree (id_empresa, estado, nombre);


-- system_pos.ejecucion_ia definition

-- Drop table

-- DROP TABLE system_pos.ejecucion_ia;

CREATE TABLE system_pos.ejecucion_ia (
	id_ejecucion_ia bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	tipo_ejecucion varchar(40) DEFAULT 'semanal'::character varying NOT NULL,
	estado varchar(30) DEFAULT 'pendiente'::character varying NOT NULL,
	fecha_inicio timestamptz NULL,
	fecha_fin timestamptz NULL,
	parametros jsonb DEFAULT '{}'::jsonb NOT NULL,
	"error" text NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_ejecucion_ia_estado CHECK (((estado)::text = ANY ((ARRAY['pendiente'::character varying, 'procesando'::character varying, 'completada'::character varying, 'fallida'::character varying])::text[]))),
	CONSTRAINT chk_ejecucion_ia_tipo CHECK (((tipo_ejecucion)::text = ANY ((ARRAY['manual'::character varying, 'semanal'::character varying, 'mensual'::character varying])::text[]))),
	CONSTRAINT ejecucion_ia_pkey PRIMARY KEY (id_ejecucion_ia),
	CONSTRAINT fk_ejecucion_ia_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE CASCADE ON UPDATE CASCADE
);


-- system_pos.familia definition

-- Drop table

-- DROP TABLE system_pos.familia;

CREATE TABLE system_pos.familia (
	id_familia bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	nombre varchar(160) NOT NULL,
	descripcion text NULL,
	estado bool DEFAULT true NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_familia_nombre CHECK ((btrim((nombre)::text) <> ''::text)),
	CONSTRAINT familia_pkey PRIMARY KEY (id_familia),
	CONSTRAINT uq_familia_empresa_id UNIQUE (id_familia, id_empresa),
	CONSTRAINT uq_familia_empresa_nombre UNIQUE (id_empresa, nombre),
	CONSTRAINT fk_familia_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_familia_empresa ON system_pos.familia USING btree (id_empresa);


-- system_pos.impuesto definition

-- Drop table

-- DROP TABLE system_pos.impuesto;

CREATE TABLE system_pos.impuesto (
	id_impuesto bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	nombre varchar(80) NOT NULL,
	tipo varchar(40) NOT NULL,
	porcentaje numeric(7, 4) DEFAULT 0 NOT NULL,
	estado bool DEFAULT true NOT NULL,
	codigo varchar(50) NULL,
	descripcion varchar(250) NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_impuesto_porcentaje CHECK ((porcentaje >= (0)::numeric)),
	CONSTRAINT chk_impuesto_porcentaje_max CHECK (((porcentaje >= (0)::numeric) AND (porcentaje <= (100)::numeric))),
	CONSTRAINT chk_impuesto_tipo CHECK (((tipo)::text = ANY ((ARRAY['iva'::character varying, 'retencion_fuente'::character varying, 'retencion_iva'::character varying, 'otro'::character varying])::text[]))),
	CONSTRAINT impuesto_pkey PRIMARY KEY (id_impuesto),
	CONSTRAINT uq_impuesto_nombre UNIQUE (id_empresa, nombre),
	CONSTRAINT fk_impuesto_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_impuesto_empresa_tipo ON system_pos.impuesto USING btree (id_empresa, tipo) WHERE (estado = true);
CREATE UNIQUE INDEX uq_impuesto_empresa_codigo ON system_pos.impuesto USING btree (id_empresa, codigo) WHERE (codigo IS NOT NULL);


-- system_pos.marca definition

-- Drop table

-- DROP TABLE system_pos.marca;

CREATE TABLE system_pos.marca (
	id_marca bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	nombre varchar(100) NOT NULL,
	descripcion varchar(250) NULL,
	estado bool DEFAULT true NOT NULL,
	fecha_creacion timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT marca_pkey PRIMARY KEY (id_marca),
	CONSTRAINT uq_marca_empresa_nombre UNIQUE (id_empresa, nombre),
	CONSTRAINT fk_marca_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_marca_empresa ON system_pos.marca USING btree (id_empresa);
CREATE INDEX idx_marca_empresa_estado ON system_pos.marca USING btree (id_empresa, estado);
CREATE INDEX idx_marca_nombre ON system_pos.marca USING btree (nombre);


-- system_pos.periodo_financiero definition

-- Drop table

-- DROP TABLE system_pos.periodo_financiero;

CREATE TABLE system_pos.periodo_financiero (
	id_periodo_financiero bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	fecha_inicio date NOT NULL,
	fecha_fin date NOT NULL,
	tipo_periodo varchar(20) DEFAULT 'mensual'::character varying NOT NULL,
	estado varchar(30) DEFAULT 'abierto'::character varying NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_periodo_financiero_estado CHECK (((estado)::text = ANY ((ARRAY['abierto'::character varying, 'cerrado'::character varying])::text[]))),
	CONSTRAINT chk_periodo_financiero_rango CHECK ((fecha_fin >= fecha_inicio)),
	CONSTRAINT chk_periodo_financiero_tipo CHECK (((tipo_periodo)::text = ANY ((ARRAY['semanal'::character varying, 'mensual'::character varying, 'trimestral'::character varying, 'anual'::character varying])::text[]))),
	CONSTRAINT periodo_financiero_pkey PRIMARY KEY (id_periodo_financiero),
	CONSTRAINT uq_periodo_financiero UNIQUE (id_empresa, fecha_inicio, fecha_fin, tipo_periodo),
	CONSTRAINT fk_periodo_financiero_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);


-- system_pos.proveedor definition

-- Drop table

-- DROP TABLE system_pos.proveedor;

CREATE TABLE system_pos.proveedor (
	id_proveedor bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	razon_social varchar(150) NOT NULL,
	nit varchar(30) NULL,
	nombre_contacto varchar(100) NULL,
	correo varchar(150) NULL,
	telefono varchar(20) NULL,
	direccion varchar(200) NULL,
	estado bool DEFAULT true NOT NULL,
	notas text NULL,
	CONSTRAINT proveedor_nit_key UNIQUE (nit),
	CONSTRAINT proveedor_pkey PRIMARY KEY (id_proveedor),
	CONSTRAINT uq_proveedor_empresa_id UNIQUE (id_proveedor, id_empresa),
	CONSTRAINT fk_proveedor_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_proveedor_empresa_estado ON system_pos.proveedor USING btree (id_empresa, estado);


-- system_pos.reporte_ia definition

-- Drop table

-- DROP TABLE system_pos.reporte_ia;

CREATE TABLE system_pos.reporte_ia (
	id_reporte_ia bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_ejecucion_ia int8 NULL,
	fecha_inicio date NOT NULL,
	fecha_fin date NOT NULL,
	titulo varchar(180) NOT NULL,
	resumen text NULL,
	estado varchar(30) DEFAULT 'generado'::character varying NOT NULL,
	contenido jsonb DEFAULT '{}'::jsonb NOT NULL,
	fecha_generacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_reporte_ia_estado CHECK (((estado)::text = ANY ((ARRAY['generado'::character varying, 'publicado'::character varying, 'archivado'::character varying])::text[]))),
	CONSTRAINT chk_reporte_ia_rango CHECK ((fecha_fin >= fecha_inicio)),
	CONSTRAINT reporte_ia_pkey PRIMARY KEY (id_reporte_ia),
	CONSTRAINT fk_reporte_ia_ejecucion FOREIGN KEY (id_ejecucion_ia) REFERENCES system_pos.ejecucion_ia(id_ejecucion_ia) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_reporte_ia_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX idx_reporte_ia_contenido_gin ON system_pos.reporte_ia USING gin (contenido);
CREATE INDEX idx_reporte_ia_empresa_fecha ON system_pos.reporte_ia USING btree (id_empresa, fecha_generacion DESC);


-- system_pos.resumen_financiero definition

-- Drop table

-- DROP TABLE system_pos.resumen_financiero;

CREATE TABLE system_pos.resumen_financiero (
	id_resumen_financiero bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_periodo_financiero int8 NOT NULL,
	total_ingresos numeric(14, 2) DEFAULT 0 NOT NULL,
	total_egresos numeric(14, 2) DEFAULT 0 NOT NULL,
	utilidad_bruta numeric(14, 2) DEFAULT 0 NOT NULL,
	impuestos numeric(14, 2) DEFAULT 0 NOT NULL,
	utilidad_neta numeric(14, 2) DEFAULT 0 NOT NULL,
	datos jsonb DEFAULT '{}'::jsonb NOT NULL,
	fecha_calculo timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	total_gastos_mercancia numeric(14, 2) DEFAULT 0 NOT NULL,
	total_gastos_servicios numeric(14, 2) DEFAULT 0 NOT NULL,
	total_gastos_otros numeric(14, 2) DEFAULT 0 NOT NULL,
	balance numeric(14, 2) DEFAULT 0 NOT NULL,
	resultado varchar(20) DEFAULT 'equilibrio'::character varying NOT NULL,
	margen_neto numeric(9, 4) DEFAULT 0 NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	utilidad_operativa numeric(14, 2) DEFAULT 0 NOT NULL,
	total_gastos_impuestos numeric(14, 2) DEFAULT 0 NOT NULL,
	impuestos_registro_neto numeric(14, 2) DEFAULT 0 NOT NULL,
	CONSTRAINT chk_resumen_financiero_resultado CHECK (((resultado)::text = ANY ((ARRAY['ganancia'::character varying, 'perdida'::character varying, 'equilibrio'::character varying])::text[]))),
	CONSTRAINT resumen_financiero_pkey PRIMARY KEY (id_resumen_financiero),
	CONSTRAINT uq_resumen_financiero_periodo UNIQUE (id_periodo_financiero),
	CONSTRAINT fk_resumen_financiero_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_resumen_financiero_periodo FOREIGN KEY (id_periodo_financiero) REFERENCES system_pos.periodo_financiero(id_periodo_financiero) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX idx_resumen_financiero_datos_gin ON system_pos.resumen_financiero USING gin (datos);
CREATE INDEX idx_resumen_financiero_empresa_fecha ON system_pos.resumen_financiero USING btree (id_empresa, fecha_calculo DESC);


-- system_pos.rol_permiso definition

-- Drop table

-- DROP TABLE system_pos.rol_permiso;

CREATE TABLE system_pos.rol_permiso (
	id_rol int8 NOT NULL,
	id_permiso int8 NOT NULL,
	fecha_asignacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT rol_permiso_pkey PRIMARY KEY (id_rol, id_permiso),
	CONSTRAINT rol_permiso_id_permiso_fkey FOREIGN KEY (id_permiso) REFERENCES system_pos.permiso(id_permiso) ON DELETE CASCADE,
	CONSTRAINT rol_permiso_id_rol_fkey FOREIGN KEY (id_rol) REFERENCES system_pos.rol(id_rol) ON DELETE CASCADE
);
CREATE INDEX idx_rol_permiso_permiso ON system_pos.rol_permiso USING btree (id_permiso, id_rol);


-- system_pos.sucursal definition

-- Drop table

-- DROP TABLE system_pos.sucursal;

CREATE TABLE system_pos.sucursal (
	id_sucursal bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	nombre varchar(100) NOT NULL,
	direccion varchar(200) NULL,
	telefono varchar(20) NULL,
	estado bool DEFAULT true NOT NULL,
	fecha_creacion timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
	tipo_negocio varchar(50) NOT NULL,
	ancho_comprobante int2 DEFAULT 80 NOT NULL,
	CONSTRAINT chk_sucursal_ancho_comprobante CHECK ((ancho_comprobante = ANY (ARRAY[58, 80]))),
	CONSTRAINT sucursal_pkey PRIMARY KEY (id_sucursal),
	CONSTRAINT uq_sucursal_empresa_id UNIQUE (id_sucursal, id_empresa),
	CONSTRAINT fk_sucursal_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_sucursal_empresa ON system_pos.sucursal USING btree (id_empresa);


-- system_pos.usuario definition

-- Drop table

-- DROP TABLE system_pos.usuario;

CREATE TABLE system_pos.usuario (
	id_usuario bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	nombre varchar(100) NOT NULL,
	apellido varchar(100) NULL,
	correo varchar(150) NULL,
	username varchar(50) NOT NULL,
	rol varchar(50) NOT NULL,
	estado bool DEFAULT true NOT NULL,
	fecha_creacion timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
	token_version int8 DEFAULT 0 NOT NULL,
	ultimo_cambio_rol timestamptz NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT uq_usuario_empresa_id UNIQUE (id_usuario, id_empresa),
	CONSTRAINT usuario_correo_key UNIQUE (correo),
	CONSTRAINT usuario_pkey PRIMARY KEY (id_usuario),
	CONSTRAINT usuario_username_key UNIQUE (username),
	CONSTRAINT fk_usuario_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_usuario_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_usuario_correo_estado ON system_pos.usuario USING btree (correo, estado);
CREATE INDEX idx_usuario_correo_lower_estado ON system_pos.usuario USING btree (lower((correo)::text), estado);
CREATE INDEX idx_usuario_empresa_creacion ON system_pos.usuario USING btree (id_empresa, fecha_creacion DESC, id_usuario DESC);
CREATE INDEX idx_usuario_username_estado ON system_pos.usuario USING btree (username, estado);
CREATE INDEX idx_usuario_username_lower_estado ON system_pos.usuario USING btree (lower((username)::text), estado);


-- system_pos.usuario_credencial definition

-- Drop table

-- DROP TABLE system_pos.usuario_credencial;

CREATE TABLE system_pos.usuario_credencial (
	id_usuario_credencial bigserial NOT NULL,
	id_usuario int8 NOT NULL,
	password_hash text NOT NULL,
	password_salt text NOT NULL,
	password_algoritmo varchar(40) DEFAULT 'scrypt'::character varying NOT NULL,
	password_parametros jsonb DEFAULT '{"keylen": 64}'::jsonb NOT NULL,
	requiere_cambio_password bool DEFAULT false NOT NULL,
	ultimo_cambio_password timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	creado_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_usuario_credencial_algoritmo CHECK (((password_algoritmo)::text = 'scrypt'::text)),
	CONSTRAINT usuario_credencial_id_usuario_key UNIQUE (id_usuario),
	CONSTRAINT usuario_credencial_pkey PRIMARY KEY (id_usuario_credencial),
	CONSTRAINT fk_usuario_credencial_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX idx_usuario_credencial_usuario ON system_pos.usuario_credencial USING btree (id_usuario);


-- system_pos.abono_cliente_lote definition

-- Drop table

-- DROP TABLE system_pos.abono_cliente_lote;

CREATE TABLE system_pos.abono_cliente_lote (
	id_abono_cliente_lote bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_cliente int8 NOT NULL,
	id_usuario int8 NOT NULL,
	monto_total numeric(14, 2) NOT NULL,
	idempotency_key uuid NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT abono_cliente_lote_pkey PRIMARY KEY (id_abono_cliente_lote),
	CONSTRAINT chk_abono_cliente_lote_monto CHECK ((monto_total > (0)::numeric)),
	CONSTRAINT uq_abono_cliente_lote_empresa_id UNIQUE (id_empresa, id_abono_cliente_lote),
	CONSTRAINT uq_abono_cliente_lote_empresa_idempotency UNIQUE (id_empresa, idempotency_key),
	CONSTRAINT fk_abono_cliente_lote_cliente_empresa FOREIGN KEY (id_empresa,id_cliente) REFERENCES system_pos.cliente(id_empresa,id_cliente) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_abono_cliente_lote_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_abono_cliente_lote_usuario_empresa FOREIGN KEY (id_usuario,id_empresa) REFERENCES system_pos.usuario(id_usuario,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);


-- system_pos.ai_report_suggestions definition

-- Drop table

-- DROP TABLE system_pos.ai_report_suggestions;

CREATE TABLE system_pos.ai_report_suggestions (
	id_ai_report_suggestion bigserial NOT NULL,
	id_ai_report int8 NOT NULL,
	id_empresa int8 NOT NULL,
	"type" varchar(80) NOT NULL,
	title varchar(180) NOT NULL,
	description text NOT NULL,
	affected_products jsonb DEFAULT '[]'::jsonb NOT NULL,
	priority varchar(30) DEFAULT 'medium'::character varying NOT NULL,
	action_suggested text NULL,
	impact_estimate text NULL,
	is_read bool DEFAULT false NOT NULL,
	read_at timestamptz NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT ai_report_suggestions_pkey PRIMARY KEY (id_ai_report_suggestion),
	CONSTRAINT chk_ai_report_suggestions_priority CHECK (((priority)::text = ANY ((ARRAY['low'::character varying, 'medium'::character varying, 'high'::character varying, 'urgent'::character varying])::text[]))),
	CONSTRAINT fk_ai_report_suggestions_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_ai_report_suggestions_report FOREIGN KEY (id_ai_report) REFERENCES system_pos.ai_reports(id_ai_report) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX idx_ai_report_suggestions_report ON system_pos.ai_report_suggestions USING btree (id_empresa, id_ai_report, created_at);
CREATE INDEX idx_ai_report_suggestions_unread ON system_pos.ai_report_suggestions USING btree (id_empresa, id_ai_report) WHERE (is_read = false);


-- system_pos.auditoria_evento definition

-- Drop table

-- DROP TABLE system_pos.auditoria_evento;

CREATE TABLE system_pos.auditoria_evento (
	id_auditoria_evento bigserial NOT NULL,
	id_empresa int8 NULL,
	id_usuario int8 NULL,
	accion varchar(120) NOT NULL,
	entidad_tipo varchar(80) NOT NULL,
	entidad_id int8 NULL,
	datos_anteriores jsonb NULL,
	datos_nuevos jsonb NULL,
	ip_origen varchar(80) NULL,
	user_agent text NULL,
	fecha_evento timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT auditoria_evento_pkey PRIMARY KEY (id_auditoria_evento),
	CONSTRAINT fk_auditoria_evento_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_auditoria_evento_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX idx_auditoria_evento_empresa_fecha ON system_pos.auditoria_evento USING btree (id_empresa, fecha_evento DESC);


-- system_pos.caja definition

-- Drop table

-- DROP TABLE system_pos.caja;

CREATE TABLE system_pos.caja (
	id_caja bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	nombre varchar(100) NOT NULL,
	estado bool DEFAULT true NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	default_opening_amount numeric(14, 2) DEFAULT 0 NOT NULL,
	CONSTRAINT caja_pkey PRIMARY KEY (id_caja),
	CONSTRAINT chk_caja_default_opening_amount CHECK ((default_opening_amount >= (0)::numeric)),
	CONSTRAINT uq_caja_id_empresa_sucursal UNIQUE (id_caja, id_empresa, id_sucursal),
	CONSTRAINT uq_caja_nombre UNIQUE (id_empresa, id_sucursal, nombre),
	CONSTRAINT fk_caja_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_caja_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_caja_sucursal_empresa FOREIGN KEY (id_sucursal,id_empresa) REFERENCES system_pos.sucursal(id_sucursal,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_caja_empresa_sucursal ON system_pos.caja USING btree (id_empresa, id_sucursal);
CREATE INDEX idx_caja_empresa_sucursal_activa ON system_pos.caja USING btree (id_empresa, id_sucursal) WHERE (estado = true);
CREATE UNIQUE INDEX uq_caja_empresa_sucursal_nombre_normalizado ON system_pos.caja USING btree (id_empresa, id_sucursal, lower(btrim((nombre)::text)));


-- system_pos.empleado definition

-- Drop table

-- DROP TABLE system_pos.empleado;

CREATE TABLE system_pos.empleado (
	id_empleado bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	id_usuario int8 NULL,
	codigo varchar(40) NULL,
	tipo_documento varchar(30) NULL,
	numero_documento varchar(50) NULL,
	nombre varchar(100) NOT NULL,
	apellido varchar(100) NULL,
	cargo varchar(100) NOT NULL,
	telefono varchar(40) NULL,
	correo varchar(180) NULL,
	fecha_ingreso date NULL,
	salario numeric(14, 2) NULL,
	turno varchar(80) NULL,
	estado varchar(30) DEFAULT 'activo'::character varying NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	id_caja int8 NULL,
	CONSTRAINT empleado_estado_check CHECK (((estado)::text = ANY ((ARRAY['activo'::character varying, 'inactivo'::character varying, 'suspendido'::character varying])::text[]))),
	CONSTRAINT empleado_pkey PRIMARY KEY (id_empleado),
	CONSTRAINT empleado_salario_check CHECK (((salario IS NULL) OR (salario >= (0)::numeric))),
	CONSTRAINT fk_empleado_caja FOREIGN KEY (id_caja,id_empresa,id_sucursal) REFERENCES system_pos.caja(id_caja,id_empresa,id_sucursal) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_empleado_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa),
	CONSTRAINT fk_empleado_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal),
	CONSTRAINT fk_empleado_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE SET NULL
);
CREATE INDEX idx_empleado_empresa_estado ON system_pos.empleado USING btree (id_empresa, estado);
CREATE INDEX idx_empleado_empresa_usuario_activo ON system_pos.empleado USING btree (id_empresa, id_usuario) WHERE ((id_usuario IS NOT NULL) AND ((estado)::text = 'activo'::text));
CREATE UNIQUE INDEX uq_empleado_empresa_codigo ON system_pos.empleado USING btree (id_empresa, codigo) WHERE (codigo IS NOT NULL);
CREATE UNIQUE INDEX uq_empleado_empresa_documento ON system_pos.empleado USING btree (id_empresa, numero_documento) WHERE (numero_documento IS NOT NULL);
CREATE UNIQUE INDEX uq_empleado_usuario ON system_pos.empleado USING btree (id_usuario) WHERE (id_usuario IS NOT NULL);


-- system_pos.gasto_recurrente definition

-- Drop table

-- DROP TABLE system_pos.gasto_recurrente;

CREATE TABLE system_pos.gasto_recurrente (
	id_gasto_recurrente bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NULL,
	id_categoria_gasto int8 NOT NULL,
	id_usuario_creador int8 NOT NULL,
	descripcion text NOT NULL,
	monto numeric(14, 2) NOT NULL,
	metodo_pago varchar(30) NULL,
	proveedor_id int8 NULL,
	proveedor_nombre varchar(150) NULL,
	tercero_nombre text NULL,
	tercero_nit text NULL,
	frecuencia varchar(20) NOT NULL,
	config_frecuencia jsonb DEFAULT '{}'::jsonb NOT NULL,
	fecha_inicio date NOT NULL,
	proxima_fecha_generacion date NOT NULL,
	activo bool DEFAULT true NOT NULL,
	fecha_pausado timestamptz NULL,
	fecha_reactivado timestamptz NULL,
	"version" int4 DEFAULT 1 NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_gasto_recurrente_fechas CHECK ((proxima_fecha_generacion >= fecha_inicio)),
	CONSTRAINT chk_gasto_recurrente_frecuencia CHECK (((frecuencia)::text = ANY ((ARRAY['diario'::character varying, 'semanal'::character varying, 'quincenal'::character varying, 'mensual'::character varying, 'trimestral'::character varying, 'semestral'::character varying, 'anual'::character varying])::text[]))),
	CONSTRAINT chk_gasto_recurrente_metodo_pago CHECK (((metodo_pago IS NULL) OR ((metodo_pago)::text = ANY ((ARRAY['efectivo'::character varying, 'tarjeta'::character varying, 'nequi'::character varying, 'daviplata'::character varying, 'transferencia'::character varying, 'credito'::character varying])::text[])))),
	CONSTRAINT chk_gasto_recurrente_monto CHECK ((monto > (0)::numeric)),
	CONSTRAINT chk_gasto_recurrente_proveedor_tercero_excluyente CHECK (((proveedor_id IS NULL) OR ((tercero_nombre IS NULL) AND (tercero_nit IS NULL)))),
	CONSTRAINT gasto_recurrente_pkey PRIMARY KEY (id_gasto_recurrente),
	CONSTRAINT fk_gasto_recurrente_categoria FOREIGN KEY (id_categoria_gasto) REFERENCES system_pos.categoria_gasto(id_categoria_gasto) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_gasto_recurrente_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_gasto_recurrente_proveedor FOREIGN KEY (proveedor_id) REFERENCES system_pos.proveedor(id_proveedor) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_gasto_recurrente_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_gasto_recurrente_usuario FOREIGN KEY (id_usuario_creador) REFERENCES system_pos.usuario(id_usuario) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_gasto_recurrente_empresa_categoria ON system_pos.gasto_recurrente USING btree (id_empresa, id_categoria_gasto);
CREATE INDEX idx_gasto_recurrente_empresa_estado ON system_pos.gasto_recurrente USING btree (id_empresa, activo, proxima_fecha_generacion);
CREATE INDEX idx_gasto_recurrente_empresa_sucursal ON system_pos.gasto_recurrente USING btree (id_empresa, id_sucursal);
CREATE INDEX idx_gasto_recurrente_pendientes ON system_pos.gasto_recurrente USING btree (proxima_fecha_generacion) WHERE (activo = true);


-- system_pos.insight_ia definition

-- Drop table

-- DROP TABLE system_pos.insight_ia;

CREATE TABLE system_pos.insight_ia (
	id_insight_ia bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_reporte_ia int8 NOT NULL,
	tipo_insight varchar(60) NOT NULL,
	titulo varchar(180) NOT NULL,
	descripcion text NOT NULL,
	severidad varchar(30) DEFAULT 'info'::character varying NOT NULL,
	datos jsonb DEFAULT '{}'::jsonb NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_insight_ia_severidad CHECK (((severidad)::text = ANY ((ARRAY['info'::character varying, 'success'::character varying, 'warning'::character varying, 'error'::character varying, 'critical'::character varying])::text[]))),
	CONSTRAINT insight_ia_pkey PRIMARY KEY (id_insight_ia),
	CONSTRAINT fk_insight_ia_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_insight_ia_reporte FOREIGN KEY (id_reporte_ia) REFERENCES system_pos.reporte_ia(id_reporte_ia) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX idx_insight_ia_datos_gin ON system_pos.insight_ia USING gin (datos);
CREATE INDEX idx_insight_ia_reporte ON system_pos.insight_ia USING btree (id_reporte_ia);


-- system_pos.jwt_token_revocado definition

-- Drop table

-- DROP TABLE system_pos.jwt_token_revocado;

CREATE TABLE system_pos.jwt_token_revocado (
	id_jwt_token_revocado bigserial NOT NULL,
	jti varchar(120) NOT NULL,
	id_usuario int8 NULL,
	expires_at timestamptz NOT NULL,
	revoked_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	motivo varchar(120) DEFAULT 'logout'::character varying NOT NULL,
	CONSTRAINT jwt_token_revocado_jti_key UNIQUE (jti),
	CONSTRAINT jwt_token_revocado_pkey PRIMARY KEY (id_jwt_token_revocado),
	CONSTRAINT fk_jwt_token_revocado_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX idx_jwt_token_revocado_expires_at ON system_pos.jwt_token_revocado USING btree (expires_at);
CREATE INDEX idx_jwt_token_revocado_jti ON system_pos.jwt_token_revocado USING btree (jti);


-- system_pos.kpi_resumen definition

-- Drop table

-- DROP TABLE system_pos.kpi_resumen;

CREATE TABLE system_pos.kpi_resumen (
	id_kpi_resumen bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NULL,
	fecha_inicio date NOT NULL,
	fecha_fin date NOT NULL,
	total_ventas numeric(14, 2) DEFAULT 0 NOT NULL,
	cantidad_ventas int8 DEFAULT 0 NOT NULL,
	ticket_promedio numeric(14, 2) DEFAULT 0 NOT NULL,
	margen_estimado numeric(14, 2) DEFAULT 0 NOT NULL,
	rotacion_inventario numeric(14, 4) DEFAULT 0 NOT NULL,
	productos_bajo_stock int8 DEFAULT 0 NOT NULL,
	datos jsonb DEFAULT '{}'::jsonb NOT NULL,
	fecha_calculo timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_kpi_resumen_rango CHECK ((fecha_fin >= fecha_inicio)),
	CONSTRAINT kpi_resumen_pkey PRIMARY KEY (id_kpi_resumen),
	CONSTRAINT fk_kpi_resumen_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_kpi_resumen_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX idx_kpi_resumen_empresa_rango ON system_pos.kpi_resumen USING btree (id_empresa, fecha_inicio, fecha_fin);


-- system_pos.metrica_venta_semanal definition

-- Drop table

-- DROP TABLE system_pos.metrica_venta_semanal;

CREATE TABLE system_pos.metrica_venta_semanal (
	id_metrica_venta_semanal bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NULL,
	semana_inicio date NOT NULL,
	semana_fin date NOT NULL,
	total_ventas numeric(14, 2) DEFAULT 0 NOT NULL,
	cantidad_ventas int8 DEFAULT 0 NOT NULL,
	ticket_promedio numeric(14, 2) DEFAULT 0 NOT NULL,
	hora_pico int2 NULL,
	dia_pico int2 NULL,
	datos jsonb DEFAULT '{}'::jsonb NOT NULL,
	fecha_calculo timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_metrica_venta_dia CHECK (((dia_pico IS NULL) OR ((dia_pico >= 1) AND (dia_pico <= 7)))),
	CONSTRAINT chk_metrica_venta_hora CHECK (((hora_pico IS NULL) OR ((hora_pico >= 0) AND (hora_pico <= 23)))),
	CONSTRAINT chk_metrica_venta_rango CHECK ((semana_fin >= semana_inicio)),
	CONSTRAINT metrica_venta_semanal_pkey PRIMARY KEY (id_metrica_venta_semanal),
	CONSTRAINT uq_metrica_venta_semanal UNIQUE (id_empresa, id_sucursal, semana_inicio, semana_fin),
	CONSTRAINT fk_metrica_venta_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_metrica_venta_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX idx_metrica_venta_empresa_rango ON system_pos.metrica_venta_semanal USING btree (id_empresa, semana_inicio DESC);


-- system_pos.notification definition

-- Drop table

-- DROP TABLE system_pos.notification;

CREATE TABLE system_pos.notification (
	id_notification bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NULL,
	id_event_type int8 NOT NULL,
	title varchar(160) NOT NULL,
	message text NOT NULL,
	severity varchar(30) DEFAULT 'info'::character varying NOT NULL,
	entity_type varchar(80) NULL,
	entity_id varchar(120) NULL,
	payload jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_by int8 NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	expires_at timestamptz NULL,
	CONSTRAINT chk_notification_severity CHECK (((severity)::text = ANY (ARRAY[('info'::character varying)::text, ('success'::character varying)::text, ('warning'::character varying)::text, ('error'::character varying)::text, ('critical'::character varying)::text]))),
	CONSTRAINT notification_pkey PRIMARY KEY (id_notification),
	CONSTRAINT fk_notification_created_by FOREIGN KEY (created_by) REFERENCES system_pos.usuario(id_usuario) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_notification_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_notification_event_type FOREIGN KEY (id_event_type) REFERENCES system_pos.notification_event_type(id_event_type) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_notification_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX idx_notification_created_at ON system_pos.notification USING btree (created_at DESC);
CREATE INDEX idx_notification_entity ON system_pos.notification USING btree (entity_type, entity_id);
CREATE INDEX idx_notification_event_type ON system_pos.notification USING btree (id_event_type);
CREATE INDEX idx_notification_payload_gin ON system_pos.notification USING gin (payload);
CREATE INDEX idx_notification_sucursal ON system_pos.notification USING btree (id_sucursal);


-- system_pos.notification_delivery_outbox definition

-- Drop table

-- DROP TABLE system_pos.notification_delivery_outbox;

CREATE TABLE system_pos.notification_delivery_outbox (
	id_notification int8 NOT NULL,
	id_usuario int8 NOT NULL,
	status varchar(30) DEFAULT 'pending'::character varying NOT NULL,
	attempts int4 DEFAULT 0 NOT NULL,
	processed_at timestamptz NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	channel varchar(30) DEFAULT 'in_app'::character varying NOT NULL,
	last_error text NULL,
	available_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	id_outbox bigserial NOT NULL,
	CONSTRAINT chk_notification_outbox_attempts CHECK ((attempts >= 0)),
	CONSTRAINT chk_notification_outbox_channel CHECK (((channel)::text = 'in_app'::text)),
	CONSTRAINT chk_notification_outbox_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'sent'::character varying, 'failed'::character varying])::text[]))),
	CONSTRAINT notification_delivery_outbox_pkey PRIMARY KEY (id_outbox),
	CONSTRAINT fk_notification_outbox_notification FOREIGN KEY (id_notification) REFERENCES system_pos.notification(id_notification) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_notification_outbox_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX idx_notification_delivery_outbox_pending ON system_pos.notification_delivery_outbox USING btree (status, created_at) WHERE ((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('failed'::character varying)::text]));
CREATE INDEX idx_notification_outbox_pending ON system_pos.notification_delivery_outbox USING btree (status, available_at) WHERE ((status)::text = ANY ((ARRAY['pending'::character varying, 'failed'::character varying])::text[]));


-- system_pos.notification_preference definition

-- Drop table

-- DROP TABLE system_pos.notification_preference;

CREATE TABLE system_pos.notification_preference (
	id_usuario int8 NOT NULL,
	id_event_type int8 NOT NULL,
	enabled bool DEFAULT true NOT NULL,
	min_severity varchar(30) DEFAULT 'info'::character varying NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	id_notification_preference bigserial NOT NULL,
	CONSTRAINT chk_notification_preference_min_severity CHECK (((min_severity)::text = ANY (ARRAY[('info'::character varying)::text, ('success'::character varying)::text, ('warning'::character varying)::text, ('error'::character varying)::text, ('critical'::character varying)::text]))),
	CONSTRAINT notification_preference_pkey PRIMARY KEY (id_notification_preference),
	CONSTRAINT uq_notification_preference_user_event UNIQUE (id_usuario, id_event_type),
	CONSTRAINT fk_notification_preference_event_type FOREIGN KEY (id_event_type) REFERENCES system_pos.notification_event_type(id_event_type) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_notification_preference_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE
);


-- system_pos.notification_recipient definition

-- Drop table

-- DROP TABLE system_pos.notification_recipient;

CREATE TABLE system_pos.notification_recipient (
	id_notification int8 NOT NULL,
	id_usuario int8 NOT NULL,
	delivered_at timestamptz NULL,
	read_at timestamptz NULL,
	deleted_at timestamptz NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	id_notification_recipient bigserial NOT NULL,
	CONSTRAINT notification_recipient_pkey PRIMARY KEY (id_notification_recipient),
	CONSTRAINT uq_notification_recipient_user UNIQUE (id_notification, id_usuario),
	CONSTRAINT fk_notification_recipient_notification FOREIGN KEY (id_notification) REFERENCES system_pos.notification(id_notification) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_notification_recipient_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX idx_notification_recipient_unread ON system_pos.notification_recipient USING btree (id_usuario, id_notification) WHERE ((read_at IS NULL) AND (deleted_at IS NULL));
CREATE INDEX idx_notification_recipient_user_all ON system_pos.notification_recipient USING btree (id_usuario, created_at DESC) WHERE (deleted_at IS NULL);
CREATE INDEX idx_notification_recipient_user_unread ON system_pos.notification_recipient USING btree (id_usuario, created_at DESC) WHERE ((read_at IS NULL) AND (deleted_at IS NULL));
CREATE INDEX idx_notification_recipient_usuario ON system_pos.notification_recipient USING btree (id_usuario, id_notification) WHERE (deleted_at IS NULL);


-- system_pos.producto definition

-- Drop table

-- DROP TABLE system_pos.producto;

CREATE TABLE system_pos.producto (
	id_producto bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_categoria int8 NOT NULL,
	nombre varchar(150) NOT NULL,
	descripcion varchar(250) NULL,
	precio_compra numeric(12, 2) DEFAULT 0 NOT NULL,
	porcentaje_ganancia numeric(7, 2) DEFAULT 0 NOT NULL,
	precio_venta numeric(12, 2) DEFAULT 0 NOT NULL,
	iva_porcentaje numeric(5, 2) DEFAULT 19 NULL,
	retencion_fuente_porcentaje numeric(5, 2) NULL,
	retencion_iva_porcentaje numeric(5, 2) NULL,
	precio_incluye_iva bool DEFAULT false NOT NULL,
	stock_minimo numeric(12, 2) DEFAULT 0 NOT NULL,
	estado bool DEFAULT true NOT NULL,
	fecha_creacion timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
	id_proveedor int8 NULL,
	unidad varchar(40) DEFAULT 'unidad'::character varying NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	id_marca int8 NOT NULL,
	slug varchar(80) NULL,
	controla_inventario bool DEFAULT true NOT NULL,
	unidad_base varchar(40) DEFAULT 'unit'::character varying NOT NULL,
	escala_unidad_base int4 DEFAULT 1 NOT NULL,
	referencia varchar(80) NULL,
	stock_minimo_base numeric(18, 6) DEFAULT 0 NOT NULL,
	CONSTRAINT chk_producto_iva_porcentaje CHECK (((iva_porcentaje IS NULL) OR ((iva_porcentaje >= (0)::numeric) AND (iva_porcentaje <= (100)::numeric)))),
	CONSTRAINT chk_producto_porcentaje_ganancia CHECK ((porcentaje_ganancia >= (0)::numeric)),
	CONSTRAINT chk_producto_precio_compra CHECK ((precio_compra >= (0)::numeric)),
	CONSTRAINT chk_producto_precio_venta CHECK ((precio_venta >= (0)::numeric)),
	CONSTRAINT chk_producto_referencia CHECK (((referencia IS NULL) OR (btrim((referencia)::text) <> ''::text))),
	CONSTRAINT chk_producto_retencion_fuente_porcentaje CHECK (((retencion_fuente_porcentaje IS NULL) OR ((retencion_fuente_porcentaje >= (0)::numeric) AND (retencion_fuente_porcentaje <= (100)::numeric)))),
	CONSTRAINT chk_producto_retencion_iva_porcentaje CHECK (((retencion_iva_porcentaje IS NULL) OR ((retencion_iva_porcentaje >= (0)::numeric) AND (retencion_iva_porcentaje <= (100)::numeric)))),
	CONSTRAINT chk_producto_stock_minimo CHECK ((stock_minimo >= (0)::numeric)),
	CONSTRAINT chk_producto_stock_minimo_base CHECK ((stock_minimo_base >= (0)::numeric)),
	CONSTRAINT producto_pkey PRIMARY KEY (id_producto),
	CONSTRAINT trg_guardar_unidad_producto TRIGGER DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT uq_producto_empresa_id UNIQUE (id_producto, id_empresa),
	CONSTRAINT uq_producto_slug UNIQUE (slug),
	CONSTRAINT fk_producto_categoria FOREIGN KEY (id_categoria) REFERENCES system_pos.categoria(id_categoria) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_producto_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_producto_marca FOREIGN KEY (id_marca) REFERENCES system_pos.marca(id_marca) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_producto_proveedor FOREIGN KEY (id_proveedor) REFERENCES system_pos.proveedor(id_proveedor) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_producto_proveedor_empresa FOREIGN KEY (id_proveedor,id_empresa) REFERENCES system_pos.proveedor(id_proveedor,id_empresa) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX idx_producto_categoria ON system_pos.producto USING btree (id_categoria);
CREATE INDEX idx_producto_empresa ON system_pos.producto USING btree (id_empresa);
CREATE INDEX idx_producto_empresa_categoria ON system_pos.producto USING btree (id_empresa, id_categoria);
CREATE INDEX idx_producto_empresa_proveedor ON system_pos.producto USING btree (id_empresa, id_proveedor);
CREATE INDEX idx_producto_marca ON system_pos.producto USING btree (id_marca);
CREATE INDEX idx_producto_nombre ON system_pos.producto USING btree (nombre);
CREATE INDEX idx_producto_nombre_unaccent ON system_pos.producto USING btree (id_empresa, lower(system_pos.immutable_unaccent((nombre)::text)));
CREATE INDEX idx_producto_proveedor ON system_pos.producto USING btree (id_proveedor);
CREATE INDEX idx_producto_slug ON system_pos.producto USING btree (slug);
CREATE UNIQUE INDEX uq_producto_empresa_referencia ON system_pos.producto USING btree (id_empresa, referencia) WHERE (referencia IS NOT NULL);

-- Table Triggers

create constraint trigger trg_guardar_unidad_producto after
insert
    or
update
    on
    system_pos.producto deferrable initially deferred for each row execute function system_pos.guardar_unidad_vendible_activa();


-- system_pos.producto_paquete definition

-- Drop table

-- DROP TABLE system_pos.producto_paquete;

CREATE TABLE system_pos.producto_paquete (
	id_producto_paquete bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_producto int8 NOT NULL,
	referencia varchar(80) NOT NULL,
	nombre varchar(120) NOT NULL,
	descripcion text NULL,
	unidades_por_paquete numeric(12, 2) NOT NULL,
	precio_paquete numeric(12, 2) NULL,
	codigo_barras varchar(80) NOT NULL,
	estado bool DEFAULT true NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	precio_compra numeric(12, 2) DEFAULT 0 NOT NULL,
	porcentaje_ganancia numeric(7, 2) DEFAULT 0 NOT NULL,
	precio_venta numeric(12, 2) DEFAULT 0 NOT NULL,
	iva_porcentaje numeric(5, 2) NULL,
	retencion_fuente_porcentaje numeric(5, 2) NULL,
	retencion_iva_porcentaje numeric(5, 2) NULL,
	precio_incluye_iva bool DEFAULT false NOT NULL,
	unidad varchar(40) DEFAULT 'unidad'::character varying NOT NULL,
	stock_minimo numeric(12, 2) DEFAULT 0 NOT NULL,
	unidades_por_item numeric(18, 6) DEFAULT 1 NOT NULL,
	CONSTRAINT chk_producto_paquete_porcentaje_ganancia CHECK ((porcentaje_ganancia >= (0)::numeric)),
	CONSTRAINT chk_producto_paquete_precio CHECK (((precio_paquete IS NULL) OR (precio_paquete >= (0)::numeric))),
	CONSTRAINT chk_producto_paquete_precio_compra CHECK ((precio_compra >= (0)::numeric)),
	CONSTRAINT chk_producto_paquete_precio_venta CHECK ((precio_venta >= (0)::numeric)),
	CONSTRAINT chk_producto_paquete_stock_minimo CHECK ((stock_minimo >= (0)::numeric)),
	CONSTRAINT chk_producto_paquete_unidad_medida CHECK (((unidad)::text = ANY ((ARRAY['unit'::character varying, 'kg'::character varying, 'g'::character varying, 'lb'::character varying, 'l'::character varying, 'ml'::character varying])::text[]))) NOT VALID,
	CONSTRAINT chk_producto_paquete_unidades CHECK ((unidades_por_paquete > (0)::numeric)),
	CONSTRAINT chk_producto_paquete_unidades_por_item_positivas CHECK ((unidades_por_item > (0)::numeric)),
	CONSTRAINT producto_paquete_pkey PRIMARY KEY (id_producto_paquete),
	CONSTRAINT trg_guardar_unidad_paquete TRIGGER DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT uq_producto_paquete_empresa_producto_id UNIQUE (id_producto_paquete, id_empresa, id_producto),
	CONSTRAINT fk_producto_paquete_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_producto_paquete_producto FOREIGN KEY (id_producto) REFERENCES system_pos.producto(id_producto) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_producto_paquete_producto_empresa FOREIGN KEY (id_producto,id_empresa) REFERENCES system_pos.producto(id_producto,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_producto_paquete_busqueda_pos ON system_pos.producto_paquete USING btree (id_empresa, estado, codigo_barras, referencia);
CREATE INDEX idx_producto_paquete_empresa_producto_estado ON system_pos.producto_paquete USING btree (id_empresa, id_producto, estado, id_producto_paquete);
CREATE INDEX idx_producto_paquete_nombre_unaccent ON system_pos.producto_paquete USING btree (id_empresa, lower(system_pos.immutable_unaccent((nombre)::text)));
CREATE INDEX idx_producto_paquete_producto ON system_pos.producto_paquete USING btree (id_empresa, id_producto, estado);
CREATE INDEX idx_producto_paquete_sku_lookup ON system_pos.producto_paquete USING btree (id_empresa, codigo_barras);
CREATE UNIQUE INDEX uq_producto_paquete_codigo_barras_activo ON system_pos.producto_paquete USING btree (id_empresa, codigo_barras) WHERE ((estado = true) AND (codigo_barras IS NOT NULL));
CREATE UNIQUE INDEX uq_producto_paquete_empresa_barcode ON system_pos.producto_paquete USING btree (id_empresa, codigo_barras) WHERE (codigo_barras IS NOT NULL);
CREATE UNIQUE INDEX uq_producto_paquete_referencia_activa ON system_pos.producto_paquete USING btree (id_empresa, id_producto, referencia) WHERE (estado = true);

-- Table Triggers

create constraint trigger trg_guardar_unidad_paquete after
insert
    or
delete
    or
update
    on
    system_pos.producto_paquete deferrable initially deferred for each row execute function system_pos.guardar_unidad_vendible_activa();


-- system_pos.producto_paquete_sku definition

-- Drop table

-- DROP TABLE system_pos.producto_paquete_sku;

CREATE TABLE system_pos.producto_paquete_sku (
	id_producto_paquete_sku bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_producto_paquete int8 NOT NULL,
	sku varchar(160) NOT NULL,
	es_principal bool DEFAULT false NOT NULL,
	estado bool DEFAULT true NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_producto_paquete_sku_no_vacio CHECK ((btrim((sku)::text) <> ''::text)),
	CONSTRAINT producto_paquete_sku_pkey PRIMARY KEY (id_producto_paquete_sku),
	CONSTRAINT trg_validar_sku_principal_producto_paquete TRIGGER DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT producto_paquete_sku_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa),
	CONSTRAINT producto_paquete_sku_id_producto_paquete_fkey FOREIGN KEY (id_producto_paquete) REFERENCES system_pos.producto_paquete(id_producto_paquete) ON DELETE CASCADE
);
CREATE INDEX idx_producto_paquete_sku_resolucion ON system_pos.producto_paquete_sku USING btree (id_empresa, id_producto_paquete, estado);
CREATE UNIQUE INDEX uq_producto_paquete_sku_empresa_codigo ON system_pos.producto_paquete_sku USING btree (id_empresa, lower(btrim((sku)::text)));
CREATE UNIQUE INDEX uq_producto_paquete_sku_principal_activo ON system_pos.producto_paquete_sku USING btree (id_producto_paquete) WHERE ((es_principal = true) AND (estado = true));

-- Table Triggers

create trigger trg_prevenir_eliminacion_fisica_sku before
delete
    on
    system_pos.producto_paquete_sku for each row execute function system_pos.prevenir_eliminacion_fisica_sku();
create trigger trg_sincronizar_codigo_barras_principal before
insert
    or
update
    on
    system_pos.producto_paquete_sku for each row execute function system_pos.sincronizar_codigo_barras_principal();
create constraint trigger trg_validar_sku_principal_producto_paquete after
insert
    or
delete
    or
update
    on
    system_pos.producto_paquete_sku deferrable initially deferred for each row execute function system_pos.validar_sku_principal_producto_paquete();


-- system_pos.recomendacion_ia definition

-- Drop table

-- DROP TABLE system_pos.recomendacion_ia;

CREATE TABLE system_pos.recomendacion_ia (
	id_recomendacion_ia bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_reporte_ia int8 NOT NULL,
	tipo_recomendacion varchar(60) NOT NULL,
	titulo varchar(180) NOT NULL,
	descripcion text NOT NULL,
	accion_sugerida text NOT NULL,
	prioridad varchar(20) DEFAULT 'media'::character varying NOT NULL,
	impacto_estimado numeric(14, 2) NULL,
	estado varchar(30) DEFAULT 'pendiente'::character varying NOT NULL,
	entidad_tipo varchar(80) NULL,
	entidad_id int8 NULL,
	datos jsonb DEFAULT '{}'::jsonb NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	fecha_resolucion timestamptz NULL,
	CONSTRAINT chk_recomendacion_ia_estado CHECK (((estado)::text = ANY ((ARRAY['pendiente'::character varying, 'aceptada'::character varying, 'rechazada'::character varying, 'aplicada'::character varying, 'archivada'::character varying])::text[]))),
	CONSTRAINT chk_recomendacion_ia_prioridad CHECK (((prioridad)::text = ANY ((ARRAY['baja'::character varying, 'media'::character varying, 'alta'::character varying, 'critica'::character varying])::text[]))),
	CONSTRAINT recomendacion_ia_pkey PRIMARY KEY (id_recomendacion_ia),
	CONSTRAINT fk_recomendacion_ia_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_recomendacion_ia_reporte FOREIGN KEY (id_reporte_ia) REFERENCES system_pos.reporte_ia(id_reporte_ia) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX idx_recomendacion_ia_datos_gin ON system_pos.recomendacion_ia USING gin (datos);
CREATE INDEX idx_recomendacion_ia_empresa_estado ON system_pos.recomendacion_ia USING btree (id_empresa, estado, prioridad);


-- system_pos.refresh_token_sesion definition

-- Drop table

-- DROP TABLE system_pos.refresh_token_sesion;

CREATE TABLE system_pos.refresh_token_sesion (
	id_refresh_token bigserial NOT NULL,
	id_usuario int8 NOT NULL,
	id_empresa int8 NOT NULL,
	token_hash varchar(96) NOT NULL,
	parent_token_hash varchar(96) NULL,
	token_version int8 DEFAULT 0 NOT NULL,
	user_agent text NULL,
	ip_address text NULL,
	issued_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	expires_at timestamptz NOT NULL,
	rotated_at timestamptz NULL,
	revoked_at timestamptz NULL,
	revoked_reason varchar(120) NULL,
	replaced_by_token_hash varchar(96) NULL,
	session_family_id varchar(64) NULL,
	family_started_at timestamptz NULL,
	absolute_expires_at timestamptz NULL,
	last_activity_at timestamptz NULL,
	CONSTRAINT chk_refresh_token_sesion_expiration CHECK ((expires_at > issued_at)),
	CONSTRAINT refresh_token_sesion_pkey PRIMARY KEY (id_refresh_token),
	CONSTRAINT uq_refresh_token_sesion_hash UNIQUE (token_hash),
	CONSTRAINT fk_refresh_token_sesion_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_refresh_token_sesion_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX idx_refresh_token_sesion_cleanup_deadline ON system_pos.refresh_token_sesion USING btree (expires_at, absolute_expires_at);
CREATE INDEX idx_refresh_token_sesion_empresa ON system_pos.refresh_token_sesion USING btree (id_empresa, issued_at DESC);
CREATE INDEX idx_refresh_token_sesion_expired ON system_pos.refresh_token_sesion USING btree (expires_at) WHERE (revoked_at IS NULL);
CREATE INDEX idx_refresh_token_sesion_family_active ON system_pos.refresh_token_sesion USING btree (session_family_id, absolute_expires_at, last_activity_at) WHERE ((revoked_at IS NULL) AND (session_family_id IS NOT NULL));
CREATE INDEX idx_refresh_token_sesion_parent ON system_pos.refresh_token_sesion USING btree (parent_token_hash) WHERE (parent_token_hash IS NOT NULL);
CREATE INDEX idx_refresh_token_sesion_usuario_activa ON system_pos.refresh_token_sesion USING btree (id_usuario, expires_at DESC) WHERE (revoked_at IS NULL);


-- system_pos.registro_impuesto definition

-- Drop table

-- DROP TABLE system_pos.registro_impuesto;

CREATE TABLE system_pos.registro_impuesto (
	id_registro_impuesto bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_impuesto int8 NOT NULL,
	origen varchar(40) NOT NULL,
	referencia_id int8 NOT NULL,
	base_gravable numeric(14, 2) DEFAULT 0 NOT NULL,
	valor_impuesto numeric(14, 2) DEFAULT 0 NOT NULL,
	fecha_registro timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	id_sucursal int8 NULL,
	porcentaje numeric(7, 4) DEFAULT 0 NOT NULL,
	naturaleza varchar(20) DEFAULT 'debito'::character varying NOT NULL,
	es_automatico bool DEFAULT false NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	creado_por int8 NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	estado varchar(30) DEFAULT 'registrado'::character varying NOT NULL,
	CONSTRAINT chk_registro_impuesto_base CHECK ((base_gravable >= (0)::numeric)),
	CONSTRAINT chk_registro_impuesto_estado CHECK (((estado)::text = ANY ((ARRAY['registrado'::character varying, 'anulado'::character varying])::text[]))),
	CONSTRAINT chk_registro_impuesto_naturaleza CHECK (((naturaleza)::text = ANY ((ARRAY['debito'::character varying, 'credito'::character varying, 'retencion'::character varying])::text[]))),
	CONSTRAINT chk_registro_impuesto_origen CHECK (((origen)::text = ANY ((ARRAY['venta'::character varying, 'compra'::character varying, 'gasto'::character varying, 'ajuste'::character varying])::text[]))),
	CONSTRAINT chk_registro_impuesto_porcentaje CHECK (((porcentaje >= (0)::numeric) AND (porcentaje <= (100)::numeric))),
	CONSTRAINT chk_registro_impuesto_valor CHECK ((valor_impuesto >= (0)::numeric)),
	CONSTRAINT registro_impuesto_pkey PRIMARY KEY (id_registro_impuesto),
	CONSTRAINT fk_registro_impuesto_creado_por FOREIGN KEY (creado_por) REFERENCES system_pos.usuario(id_usuario) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_registro_impuesto_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_registro_impuesto_impuesto FOREIGN KEY (id_impuesto) REFERENCES system_pos.impuesto(id_impuesto) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_registro_impuesto_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX idx_registro_impuesto_empresa_fecha ON system_pos.registro_impuesto USING btree (id_empresa, fecha_registro DESC);
CREATE INDEX idx_registro_impuesto_empresa_tipo_fecha ON system_pos.registro_impuesto USING btree (id_empresa, id_impuesto, fecha_registro DESC) WHERE ((estado)::text = 'registrado'::text);
CREATE INDEX idx_registro_impuesto_financial_range ON system_pos.registro_impuesto USING btree (id_empresa, fecha_registro DESC);
CREATE INDEX idx_registro_impuesto_origen_referencia ON system_pos.registro_impuesto USING btree (origen, referencia_id) WHERE ((estado)::text = 'registrado'::text);


-- system_pos.saldo_inventario_producto_sucursal_base definition

-- Drop table

-- DROP TABLE system_pos.saldo_inventario_producto_sucursal_base;

CREATE TABLE system_pos.saldo_inventario_producto_sucursal_base (
	id_saldo_inventario_producto_base int8 DEFAULT nextval('system_pos.seq_saldo_producto_sucursal_base'::regclass) NOT NULL,
	id_empresa int8 NOT NULL,
	id_producto int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	stock_base_disponible numeric(18, 6) DEFAULT 0 NOT NULL,
	stock_base_reservado numeric(18, 6) DEFAULT 0 NOT NULL,
	"version" int4 DEFAULT 0 NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_saldo_inventario_producto_base_no_negativo CHECK (((stock_base_disponible >= (0)::numeric) AND (stock_base_reservado >= (0)::numeric))),
	CONSTRAINT chk_saldo_inventario_producto_base_version CHECK ((version >= 0)),
	CONSTRAINT saldo_inventario_producto_sucursal_base_pkey PRIMARY KEY (id_saldo_inventario_producto_base),
	CONSTRAINT uq_saldo_inventario_producto_base_scope UNIQUE (id_empresa, id_producto, id_sucursal),
	CONSTRAINT uq_saldo_inventario_producto_base_scope_id UNIQUE (id_saldo_inventario_producto_base, id_empresa, id_producto, id_sucursal),
	CONSTRAINT fk_saldo_inventario_producto_base_producto_empresa FOREIGN KEY (id_producto,id_empresa) REFERENCES system_pos.producto(id_producto,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_saldo_inventario_producto_base_sucursal_empresa FOREIGN KEY (id_sucursal,id_empresa) REFERENCES system_pos.sucursal(id_sucursal,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_saldo_inventario_producto_base_empresa_sucursal ON system_pos.saldo_inventario_producto_sucursal_base USING btree (id_empresa, id_sucursal, id_producto);


-- system_pos.secuencia_comprobante definition

-- Drop table

-- DROP TABLE system_pos.secuencia_comprobante;

CREATE TABLE system_pos.secuencia_comprobante (
	id_secuencia_comprobante bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	tipo_comprobante varchar(40) NOT NULL,
	prefijo varchar(20) DEFAULT 'POS'::character varying NOT NULL,
	consecutivo_actual int8 DEFAULT 0 NOT NULL,
	estado bool DEFAULT true NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_secuencia_comprobante_consecutivo CHECK ((consecutivo_actual >= 0)),
	CONSTRAINT chk_secuencia_comprobante_tipo CHECK (((tipo_comprobante)::text = ANY ((ARRAY['venta'::character varying, 'devolucion'::character varying, 'cierre_caja'::character varying])::text[]))),
	CONSTRAINT secuencia_comprobante_pkey PRIMARY KEY (id_secuencia_comprobante),
	CONSTRAINT uq_secuencia_comprobante UNIQUE (id_empresa, id_sucursal, tipo_comprobante, prefijo),
	CONSTRAINT fk_secuencia_comprobante_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_secuencia_comprobante_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE RESTRICT ON UPDATE CASCADE
);


-- system_pos.sesion_caja definition

-- Drop table

-- DROP TABLE system_pos.sesion_caja;

CREATE TABLE system_pos.sesion_caja (
	id_sesion_caja bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_caja int8 NOT NULL,
	id_usuario_apertura int8 NOT NULL,
	id_usuario_cierre int8 NULL,
	fecha_apertura timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	fecha_cierre timestamptz NULL,
	monto_apertura numeric(14, 2) DEFAULT 0 NOT NULL,
	monto_cierre numeric(14, 2) NULL,
	estado varchar(30) DEFAULT 'abierta'::character varying NOT NULL,
	observacion text NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_sesion_caja_estado CHECK (((estado)::text = ANY ((ARRAY['abierta'::character varying, 'cerrada'::character varying, 'anulada'::character varying])::text[]))),
	CONSTRAINT chk_sesion_caja_monto_apertura CHECK ((monto_apertura >= (0)::numeric)),
	CONSTRAINT sesion_caja_pkey PRIMARY KEY (id_sesion_caja),
	CONSTRAINT uq_sesion_caja_empresa_id UNIQUE (id_empresa, id_sesion_caja),
	CONSTRAINT fk_sesion_caja_caja FOREIGN KEY (id_caja) REFERENCES system_pos.caja(id_caja) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_sesion_caja_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_sesion_caja_usuario_apertura FOREIGN KEY (id_usuario_apertura) REFERENCES system_pos.usuario(id_usuario) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_sesion_caja_usuario_cierre FOREIGN KEY (id_usuario_cierre) REFERENCES system_pos.usuario(id_usuario) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_sesion_caja_empresa_estado ON system_pos.sesion_caja USING btree (id_empresa, estado, fecha_apertura DESC);


-- system_pos.stock_notification_rule definition

-- Drop table

-- DROP TABLE system_pos.stock_notification_rule;

CREATE TABLE system_pos.stock_notification_rule (
	id_stock_notification_rule bigserial NOT NULL,
	id_producto int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	min_stock numeric(12, 2) NOT NULL,
	cooldown_minutes int4 DEFAULT 60 NOT NULL,
	last_triggered_at timestamptz NULL,
	enabled bool DEFAULT true NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_stock_notification_rule_cooldown CHECK ((cooldown_minutes >= 0)),
	CONSTRAINT chk_stock_notification_rule_min_stock CHECK ((min_stock >= (0)::numeric)),
	CONSTRAINT stock_notification_rule_pkey PRIMARY KEY (id_stock_notification_rule),
	CONSTRAINT uq_stock_notification_rule_product_branch UNIQUE (id_producto, id_sucursal),
	CONSTRAINT fk_stock_notification_rule_producto FOREIGN KEY (id_producto) REFERENCES system_pos.producto(id_producto) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_stock_notification_rule_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX idx_stock_notification_rule_enabled ON system_pos.stock_notification_rule USING btree (id_producto, id_sucursal) WHERE (enabled = true);
CREATE INDEX idx_stock_notification_rule_product_branch ON system_pos.stock_notification_rule USING btree (id_producto, id_sucursal) WHERE (enabled = true);


-- system_pos.venta definition

-- Drop table

-- DROP TABLE system_pos.venta;

CREATE TABLE system_pos.venta (
	id_venta bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	id_cliente int8 NULL,
	id_usuario int8 NOT NULL,
	id_metodo_pago int8 NULL,
	numero_venta varchar(50) NOT NULL,
	fecha_venta timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
	subtotal numeric(14, 2) DEFAULT 0 NOT NULL,
	impuesto numeric(14, 2) DEFAULT 0 NOT NULL,
	total numeric(14, 2) DEFAULT 0 NOT NULL,
	estado varchar(30) DEFAULT 'completada'::character varying NOT NULL,
	observacion text NULL,
	estado_devolucion varchar(30) DEFAULT 'sin_devolucion'::character varying NOT NULL,
	numero_factura varchar(100) NULL,
	factura_emitida_en timestamptz NULL,
	client_sale_id uuid NULL,
	venta_offline bool DEFAULT false NOT NULL,
	sincronizada_en timestamptz NULL,
	descuento numeric(14, 2) DEFAULT 0 NOT NULL,
	condicion_pago varchar(20) DEFAULT 'contado'::character varying NOT NULL,
	estado_pago varchar(20) DEFAULT 'pagada'::character varying NOT NULL,
	monto_abonado numeric(14, 2) DEFAULT 0 NOT NULL,
	saldo_pendiente numeric(14, 2) DEFAULT 0 NOT NULL,
	monto_devuelto_credito numeric(14, 2) DEFAULT 0 NOT NULL,
	id_sesion_caja int8 NULL,
	monto_recibido numeric(14, 2) NULL,
	CONSTRAINT chk_venta_condicion_pago_credito CHECK (((condicion_pago)::text = ANY ((ARRAY['contado'::character varying, 'credito'::character varying])::text[]))) NOT VALID,
	CONSTRAINT chk_venta_descuento CHECK ((descuento >= (0)::numeric)),
	CONSTRAINT chk_venta_estado CHECK (((estado)::text = ANY ((ARRAY['registrada'::character varying, 'completada'::character varying, 'anulada'::character varying, 'cancelada'::character varying])::text[]))) NOT VALID,
	CONSTRAINT chk_venta_estado_devolucion CHECK (((estado_devolucion)::text = ANY ((ARRAY['sin_devolucion'::character varying, 'parcial'::character varying, 'total'::character varying])::text[]))),
	CONSTRAINT chk_venta_estado_pago_credito CHECK (((estado_pago)::text = ANY ((ARRAY['pagada'::character varying, 'pendiente'::character varying, 'abonada'::character varying])::text[]))) NOT VALID,
	CONSTRAINT chk_venta_impuesto CHECK ((impuesto >= (0)::numeric)),
	CONSTRAINT chk_venta_metodo_pago_contado CHECK ((((condicion_pago)::text <> 'contado'::text) OR (id_metodo_pago IS NOT NULL))),
	CONSTRAINT chk_venta_monto_recibido CHECK (((monto_recibido IS NULL) OR (monto_recibido >= (0)::numeric))),
	CONSTRAINT chk_venta_saldo_credito CHECK (((monto_abonado >= (0)::numeric) AND (monto_devuelto_credito >= (0)::numeric) AND (saldo_pendiente >= (0)::numeric) AND ((monto_abonado + monto_devuelto_credito) <= total) AND (saldo_pendiente = ((total - monto_abonado) - monto_devuelto_credito)) AND ((((estado_pago)::text = 'pagada'::text) AND (saldo_pendiente = (0)::numeric)) OR (((estado_pago)::text = 'pendiente'::text) AND (monto_abonado = (0)::numeric) AND (saldo_pendiente > (0)::numeric)) OR (((estado_pago)::text = 'abonada'::text) AND (monto_abonado > (0)::numeric) AND (saldo_pendiente > (0)::numeric))) AND (((condicion_pago)::text <> 'contado'::text) OR (((estado_pago)::text = 'pagada'::text) AND (monto_abonado = total))))) NOT VALID,
	CONSTRAINT chk_venta_subtotal CHECK ((subtotal >= (0)::numeric)),
	CONSTRAINT chk_venta_total CHECK ((total >= (0)::numeric)),
	CONSTRAINT uq_venta_empresa_id UNIQUE (id_empresa, id_venta),
	CONSTRAINT venta_pkey PRIMARY KEY (id_venta),
	CONSTRAINT fk_venta_cliente FOREIGN KEY (id_cliente) REFERENCES system_pos.cliente(id_cliente) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_venta_cliente_empresa_credito FOREIGN KEY (id_empresa,id_cliente) REFERENCES system_pos.cliente(id_empresa,id_cliente) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_venta_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_venta_metodo_pago FOREIGN KEY (id_metodo_pago) REFERENCES system_pos.metodo_pago(id_metodo_pago) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_venta_sesion_caja_empresa FOREIGN KEY (id_empresa,id_sesion_caja) REFERENCES system_pos.sesion_caja(id_empresa,id_sesion_caja) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_venta_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_venta_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_venta_cliente ON system_pos.venta USING btree (id_cliente);
CREATE INDEX idx_venta_credito_estado_pago ON system_pos.venta USING btree (id_empresa, estado_pago, fecha_venta DESC) WHERE ((condicion_pago)::text = 'credito'::text);
CREATE INDEX idx_venta_cuentas_cobrar ON system_pos.venta USING btree (id_empresa, id_cliente, saldo_pendiente DESC, fecha_venta DESC) WHERE (((condicion_pago)::text = 'credito'::text) AND (saldo_pendiente > (0)::numeric));
CREATE INDEX idx_venta_empresa_fecha ON system_pos.venta USING btree (id_empresa, fecha_venta DESC);
CREATE INDEX idx_venta_empresa_offline_fecha ON system_pos.venta USING btree (id_empresa, venta_offline, fecha_venta DESC);
CREATE INDEX idx_venta_fecha ON system_pos.venta USING btree (fecha_venta DESC);
CREATE INDEX idx_venta_resumen_empleado ON system_pos.venta USING btree (id_empresa, id_usuario, fecha_venta DESC);
CREATE INDEX idx_venta_sesion_caja ON system_pos.venta USING btree (id_empresa, id_sesion_caja) WHERE (id_sesion_caja IS NOT NULL);
CREATE UNIQUE INDEX uq_venta_empresa_client_sale_id ON system_pos.venta USING btree (id_empresa, client_sale_id) WHERE (client_sale_id IS NOT NULL);
CREATE UNIQUE INDEX uq_venta_empresa_numero ON system_pos.venta USING btree (id_empresa, numero_venta);
CREATE UNIQUE INDEX uq_venta_empresa_numero_factura ON system_pos.venta USING btree (id_empresa, numero_factura) WHERE (numero_factura IS NOT NULL);

-- Table Triggers

create trigger trg_auditar_modificacion_venta after
update
    on
    system_pos.venta for each row execute function system_pos.auditar_modificacion_venta();
create trigger trg_sincronizar_estado_pago_venta before
insert
    or
update
    of total,
    id_cliente,
    id_metodo_pago,
    condicion_pago,
    estado_pago,
    monto_abonado,
    saldo_pendiente,
    monto_devuelto_credito on
    system_pos.venta for each row execute function system_pos.sincronizar_estado_pago_venta();


-- system_pos.compra definition

-- Drop table

-- DROP TABLE system_pos.compra;

CREATE TABLE system_pos.compra (
	id_compra bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	id_proveedor int8 NULL,
	id_usuario int8 NOT NULL,
	numero_factura varchar(50) NULL,
	fecha_compra timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
	subtotal numeric(14, 2) DEFAULT 0 NOT NULL,
	impuesto numeric(14, 2) DEFAULT 0 NOT NULL,
	total numeric(14, 2) DEFAULT 0 NOT NULL,
	estado varchar(30) DEFAULT 'registrada'::character varying NOT NULL,
	observacion text NULL,
	proveedor_nombre varchar(180) NULL,
	monto_abonado numeric(14, 2) DEFAULT 0 NOT NULL,
	saldo_pendiente numeric(14, 2) DEFAULT 0 NOT NULL,
	id_sesion_caja int8 NULL,
	client_purchase_id uuid NULL,
	CONSTRAINT chk_compra_abonos CHECK (((monto_abonado >= (0)::numeric) AND (monto_abonado <= total) AND (saldo_pendiente = GREATEST((total - monto_abonado), (0)::numeric)) AND (((estado)::text <> 'abonada'::text) OR ((monto_abonado > (0)::numeric) AND (monto_abonado < total))) AND (((estado)::text <> 'pagada'::text) OR (monto_abonado = total)))),
	CONSTRAINT chk_compra_estado CHECK (((estado)::text = ANY ((ARRAY['pendiente'::character varying, 'pagada'::character varying, 'abonada'::character varying, 'cancelada'::character varying])::text[]))),
	CONSTRAINT chk_compra_impuesto CHECK ((impuesto >= (0)::numeric)),
	CONSTRAINT chk_compra_subtotal CHECK ((subtotal >= (0)::numeric)),
	CONSTRAINT chk_compra_total CHECK ((total >= (0)::numeric)),
	CONSTRAINT compra_pkey PRIMARY KEY (id_compra),
	CONSTRAINT fk_compra_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_compra_proveedor FOREIGN KEY (id_proveedor) REFERENCES system_pos.proveedor(id_proveedor) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_compra_sesion_caja_empresa FOREIGN KEY (id_empresa,id_sesion_caja) REFERENCES system_pos.sesion_caja(id_empresa,id_sesion_caja) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_compra_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_compra_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_compra_empresa_fecha ON system_pos.compra USING btree (id_empresa, fecha_compra DESC);
CREATE INDEX idx_compra_fecha ON system_pos.compra USING btree (fecha_compra DESC);
CREATE INDEX idx_compra_filtros_operativos ON system_pos.compra USING btree (id_empresa, id_sucursal, estado, fecha_compra DESC);
CREATE INDEX idx_compra_proveedor ON system_pos.compra USING btree (id_proveedor);
CREATE INDEX idx_compra_sesion_caja ON system_pos.compra USING btree (id_empresa, id_sesion_caja) WHERE (id_sesion_caja IS NOT NULL);
CREATE UNIQUE INDEX uq_compra_empresa_client_purchase_id ON system_pos.compra USING btree (id_empresa, client_purchase_id) WHERE (client_purchase_id IS NOT NULL);
CREATE UNIQUE INDEX uq_compra_empresa_otro_factura ON system_pos.compra USING btree (id_empresa, lower((proveedor_nombre)::text), numero_factura) WHERE ((id_proveedor IS NULL) AND (proveedor_nombre IS NOT NULL));
CREATE UNIQUE INDEX uq_compra_empresa_proveedor_factura ON system_pos.compra USING btree (id_empresa, id_proveedor, numero_factura) WHERE (id_proveedor IS NOT NULL);

-- Table Triggers

create trigger trg_calcular_saldo_compra before
insert
    or
update
    of total,
    estado,
    monto_abonado on
    system_pos.compra for each row execute function system_pos.calcular_saldo_compra();
create trigger trg_purchase_expense_sync after
insert
    or
update
    of id_empresa,
    id_sucursal,
    id_proveedor,
    proveedor_nombre,
    id_usuario,
    numero_factura,
    fecha_compra,
    impuesto,
    total,
    estado on
    system_pos.compra for each row execute function system_pos.sync_purchase_expense_trigger();


-- system_pos.comprobante_venta definition

-- Drop table

-- DROP TABLE system_pos.comprobante_venta;

CREATE TABLE system_pos.comprobante_venta (
	id_comprobante_venta bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_venta int8 NOT NULL,
	numero_comprobante varchar(80) NOT NULL,
	tipo_comprobante varchar(40) DEFAULT 'venta'::character varying NOT NULL,
	contenido jsonb DEFAULT '{}'::jsonb NOT NULL,
	fecha_emision timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT comprobante_venta_pkey PRIMARY KEY (id_comprobante_venta),
	CONSTRAINT uq_comprobante_venta_numero UNIQUE (id_empresa, numero_comprobante),
	CONSTRAINT fk_comprobante_venta_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_comprobante_venta_venta FOREIGN KEY (id_venta) REFERENCES system_pos.venta(id_venta) ON DELETE CASCADE ON UPDATE CASCADE
);


-- system_pos.conciliacion_caja definition

-- Drop table

-- DROP TABLE system_pos.conciliacion_caja;

CREATE TABLE system_pos.conciliacion_caja (
	id_conciliacion_caja bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sesion_caja int8 NOT NULL,
	id_usuario int8 NOT NULL,
	saldo_sistema numeric(14, 2) NOT NULL,
	saldo_fisico numeric(14, 2) NOT NULL,
	diferencia numeric(14, 2) NOT NULL,
	estado varchar(30) NOT NULL,
	observacion text NULL,
	desglose jsonb DEFAULT '{}'::jsonb NOT NULL,
	fecha_conciliacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	detalle_conciliacion jsonb DEFAULT '{}'::jsonb NOT NULL,
	CONSTRAINT chk_conciliacion_estado CHECK (((estado)::text = ANY ((ARRAY['cuadrada'::character varying, 'sobrante'::character varying, 'faltante'::character varying])::text[]))),
	CONSTRAINT chk_conciliacion_saldos CHECK ((saldo_fisico >= (0)::numeric)),
	CONSTRAINT conciliacion_caja_pkey PRIMARY KEY (id_conciliacion_caja),
	CONSTRAINT uq_conciliacion_caja_sesion UNIQUE (id_sesion_caja),
	CONSTRAINT fk_conciliacion_caja_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_conciliacion_caja_sesion FOREIGN KEY (id_sesion_caja) REFERENCES system_pos.sesion_caja(id_sesion_caja) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_conciliacion_caja_sesion_empresa FOREIGN KEY (id_empresa,id_sesion_caja) REFERENCES system_pos.sesion_caja(id_empresa,id_sesion_caja) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_conciliacion_caja_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_conciliacion_caja_empresa_fecha ON system_pos.conciliacion_caja USING btree (id_empresa, fecha_conciliacion DESC);


-- system_pos.conversion_presentacion_producto definition

-- Drop table

-- DROP TABLE system_pos.conversion_presentacion_producto;

CREATE TABLE system_pos.conversion_presentacion_producto (
	id_conversion_presentacion_producto int8 DEFAULT nextval('system_pos.seq_conversion_presentacion_producto'::regclass) NOT NULL,
	id_empresa int8 NOT NULL,
	id_producto int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	id_usuario int8 NULL,
	id_producto_paquete_origen int8 NULL,
	id_producto_paquete_destino int8 NULL,
	cantidad_base_entrada numeric(18, 6) DEFAULT 0 NOT NULL,
	cantidad_base_salida numeric(18, 6) DEFAULT 0 NOT NULL,
	motivo text NOT NULL,
	referencia varchar(120) NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_conversion_presentacion_producto_cantidades CHECK (((cantidad_base_entrada >= (0)::numeric) AND (cantidad_base_salida >= (0)::numeric) AND ((cantidad_base_entrada > (0)::numeric) OR (cantidad_base_salida > (0)::numeric)))),
	CONSTRAINT conversion_presentacion_producto_pkey PRIMARY KEY (id_conversion_presentacion_producto),
	CONSTRAINT fk_conversion_presentacion_producto_destino FOREIGN KEY (id_producto_paquete_destino,id_empresa,id_producto) REFERENCES system_pos.producto_paquete(id_producto_paquete,id_empresa,id_producto) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_conversion_presentacion_producto_origen FOREIGN KEY (id_producto_paquete_origen,id_empresa,id_producto) REFERENCES system_pos.producto_paquete(id_producto_paquete,id_empresa,id_producto) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_conversion_presentacion_producto_producto_empresa FOREIGN KEY (id_producto,id_empresa) REFERENCES system_pos.producto(id_producto,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_conversion_presentacion_producto_sucursal_empresa FOREIGN KEY (id_sucursal,id_empresa) REFERENCES system_pos.sucursal(id_sucursal,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_conversion_presentacion_producto_usuario_empresa FOREIGN KEY (id_usuario,id_empresa) REFERENCES system_pos.usuario(id_usuario,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_conversion_presentacion_producto_scope_fecha ON system_pos.conversion_presentacion_producto USING btree (id_empresa, id_producto, id_sucursal, creado_en DESC);


-- system_pos.detalle_compra definition

-- Drop table

-- DROP TABLE system_pos.detalle_compra;

CREATE TABLE system_pos.detalle_compra (
	id_detalle_compra bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_compra int8 NOT NULL,
	id_producto int8 NOT NULL,
	cantidad numeric(12, 2) NOT NULL,
	costo_unitario numeric(12, 2) NOT NULL,
	subtotal numeric(14, 2) NOT NULL,
	id_producto_paquete int8 NOT NULL,
	cantidad_compra numeric(14, 3) NOT NULL,
	unidad_compra varchar(20) NOT NULL,
	factor_conversion numeric(18, 8) NOT NULL,
	CONSTRAINT chk_detalle_compra_cantidad CHECK ((cantidad > (0)::numeric)),
	CONSTRAINT chk_detalle_compra_conversion CHECK (((cantidad_compra > (0)::numeric) AND (factor_conversion > (0)::numeric) AND (cantidad > (0)::numeric))),
	CONSTRAINT chk_detalle_compra_costo CHECK ((costo_unitario >= (0)::numeric)),
	CONSTRAINT chk_detalle_compra_subtotal CHECK ((subtotal >= (0)::numeric)),
	CONSTRAINT detalle_compra_pkey PRIMARY KEY (id_detalle_compra),
	CONSTRAINT uq_detalle_compra_empresa_id UNIQUE (id_detalle_compra, id_empresa),
	CONSTRAINT fk_detalle_compra_compra FOREIGN KEY (id_compra) REFERENCES system_pos.compra(id_compra) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_detalle_compra_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_detalle_compra_producto FOREIGN KEY (id_producto) REFERENCES system_pos.producto(id_producto) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_detalle_compra_producto_paquete FOREIGN KEY (id_producto_paquete) REFERENCES system_pos.producto_paquete(id_producto_paquete) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_detalle_compra_compra ON system_pos.detalle_compra USING btree (id_compra);
CREATE INDEX idx_detalle_compra_empresa_compra ON system_pos.detalle_compra USING btree (id_empresa, id_compra);
CREATE INDEX idx_detalle_compra_sellable ON system_pos.detalle_compra USING btree (id_producto_paquete);

-- Table Triggers

create trigger trg_completar_medida_detalle_compra before
insert
    or
update
    of cantidad,
    cantidad_compra,
    unidad_compra,
    factor_conversion on
    system_pos.detalle_compra for each row execute function system_pos.completar_medida_detalle_compra();


-- system_pos.detalle_venta definition

-- Drop table

-- DROP TABLE system_pos.detalle_venta;

CREATE TABLE system_pos.detalle_venta (
	id_detalle_venta bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_venta int8 NOT NULL,
	id_producto int8 NOT NULL,
	cantidad numeric(12, 2) NOT NULL,
	precio_unitario numeric(12, 2) NOT NULL,
	subtotal numeric(14, 2) NOT NULL,
	id_paquete_producto int8 NULL,
	sku_escaneado varchar(160) NULL,
	descuento numeric(12, 2) DEFAULT 0 NOT NULL,
	nombre_producto_historico varchar(120) NULL,
	unidad_base_producto_historica varchar(40) NULL,
	unidades_por_item_usadas numeric(18, 6) NULL,
	CONSTRAINT chk_detalle_venta_cantidad CHECK ((cantidad > (0)::numeric)),
	CONSTRAINT chk_detalle_venta_descuento CHECK ((descuento >= (0)::numeric)),
	CONSTRAINT chk_detalle_venta_precio CHECK ((precio_unitario >= (0)::numeric)),
	CONSTRAINT chk_detalle_venta_producto_snapshot_completo CHECK (((id_paquete_producto IS NULL) OR ((NULLIF(btrim((nombre_producto_historico)::text), ''::text) IS NOT NULL) AND (NULLIF(btrim((unidad_base_producto_historica)::text), ''::text) IS NOT NULL) AND (unidades_por_item_usadas IS NOT NULL) AND (unidades_por_item_usadas > (0)::numeric)))) NOT VALID,
	CONSTRAINT chk_detalle_venta_subtotal CHECK ((subtotal >= (0)::numeric)),
	CONSTRAINT detalle_venta_pkey PRIMARY KEY (id_detalle_venta),
	CONSTRAINT fk_detalle_venta_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_detalle_venta_paquete_producto FOREIGN KEY (id_paquete_producto) REFERENCES system_pos.producto_paquete(id_producto_paquete) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_detalle_venta_producto FOREIGN KEY (id_producto) REFERENCES system_pos.producto(id_producto) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_detalle_venta_venta FOREIGN KEY (id_venta) REFERENCES system_pos.venta(id_venta) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX idx_detalle_venta_empresa_producto_historica ON system_pos.detalle_venta USING btree (id_empresa, id_producto, id_detalle_venta) WHERE (nombre_producto_historico IS NOT NULL);
CREATE INDEX idx_detalle_venta_empresa_venta ON system_pos.detalle_venta USING btree (id_empresa, id_venta);
CREATE INDEX idx_detalle_venta_paquete_producto ON system_pos.detalle_venta USING btree (id_paquete_producto) WHERE (id_paquete_producto IS NOT NULL);
CREATE INDEX idx_detalle_venta_venta ON system_pos.detalle_venta USING btree (id_venta);

-- Table Triggers

create trigger trg_validar_snapshot_producto_detalle_venta before
insert
    or
update
    on
    system_pos.detalle_venta for each row execute function system_pos.validar_snapshot_producto_detalle_venta();


-- system_pos.devolucion_venta definition

-- Drop table

-- DROP TABLE system_pos.devolucion_venta;

CREATE TABLE system_pos.devolucion_venta (
	id_devolucion_venta bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_venta int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	id_usuario int8 NOT NULL,
	id_sesion_caja int8 NULL,
	motivo text NOT NULL,
	total numeric(12, 2) NOT NULL,
	estado varchar(30) DEFAULT 'completada'::character varying NOT NULL,
	fecha_devolucion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	monto_reembolsado numeric(12, 2) DEFAULT 0 NOT NULL,
	idempotency_key uuid NULL,
	CONSTRAINT chk_devolucion_venta_reembolso CHECK (((monto_reembolsado >= (0)::numeric) AND (monto_reembolsado <= total))) NOT VALID,
	CONSTRAINT devolucion_venta_estado_check CHECK (((estado)::text = ANY ((ARRAY['completada'::character varying, 'anulada'::character varying])::text[]))),
	CONSTRAINT devolucion_venta_pkey PRIMARY KEY (id_devolucion_venta),
	CONSTRAINT devolucion_venta_total_check CHECK ((total >= (0)::numeric)),
	CONSTRAINT uq_devolucion_venta_empresa_idempotency UNIQUE (id_empresa, idempotency_key),
	CONSTRAINT fk_devolucion_venta_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa),
	CONSTRAINT fk_devolucion_venta_sesion FOREIGN KEY (id_sesion_caja) REFERENCES system_pos.sesion_caja(id_sesion_caja),
	CONSTRAINT fk_devolucion_venta_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal),
	CONSTRAINT fk_devolucion_venta_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario),
	CONSTRAINT fk_devolucion_venta_venta FOREIGN KEY (id_venta) REFERENCES system_pos.venta(id_venta)
);
CREATE INDEX idx_devolucion_venta_sale ON system_pos.devolucion_venta USING btree (id_empresa, id_venta, fecha_devolucion DESC);

-- Table Triggers

create trigger trg_recalcular_saldo_venta_desde_devolucion after
insert
    or
delete
    or
update
    of total on
    system_pos.devolucion_venta for each row execute function system_pos.recalcular_saldo_venta_desde_devolucion();


-- system_pos.familia_producto definition

-- Drop table

-- DROP TABLE system_pos.familia_producto;

CREATE TABLE system_pos.familia_producto (
	id_familia int8 NOT NULL,
	id_empresa int8 NOT NULL,
	id_producto int8 NOT NULL,
	orden int4 DEFAULT 0 NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_familia_producto_orden CHECK ((orden >= 0)),
	CONSTRAINT familia_producto_pkey PRIMARY KEY (id_familia, id_producto),
	CONSTRAINT fk_familia_producto_familia_empresa FOREIGN KEY (id_familia,id_empresa) REFERENCES system_pos.familia(id_familia,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_familia_producto_producto_empresa FOREIGN KEY (id_producto,id_empresa) REFERENCES system_pos.producto(id_producto,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_familia_producto_empresa_producto ON system_pos.familia_producto USING btree (id_empresa, id_producto);


-- system_pos.historial_modificacion_venta definition

-- Drop table

-- DROP TABLE system_pos.historial_modificacion_venta;

CREATE TABLE system_pos.historial_modificacion_venta (
	id_historial_venta bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_venta int8 NOT NULL,
	id_usuario int8 NULL,
	campos_modificados _text DEFAULT ARRAY[]::text[] NOT NULL,
	datos_anteriores jsonb NOT NULL,
	datos_nuevos jsonb NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT historial_modificacion_venta_pkey PRIMARY KEY (id_historial_venta),
	CONSTRAINT historial_modificacion_venta_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT,
	CONSTRAINT historial_modificacion_venta_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE SET NULL,
	CONSTRAINT historial_modificacion_venta_id_venta_fkey FOREIGN KEY (id_venta) REFERENCES system_pos.venta(id_venta) ON DELETE CASCADE
);
CREATE INDEX idx_historial_venta_empresa_venta ON system_pos.historial_modificacion_venta USING btree (id_empresa, id_venta, creado_en DESC);


-- system_pos.lote_inventario_producto definition

-- Drop table

-- DROP TABLE system_pos.lote_inventario_producto;

CREATE TABLE system_pos.lote_inventario_producto (
	id_lote_inventario_producto int8 DEFAULT nextval('system_pos.seq_lote_inventario_producto'::regclass) NOT NULL,
	id_saldo_inventario_producto_base int8 NOT NULL,
	id_empresa int8 NOT NULL,
	id_producto int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	id_producto_paquete_recepcion int8 NULL,
	codigo_lote varchar(80) NOT NULL,
	fecha_vencimiento date NULL,
	cantidad_base_inicial numeric(18, 6) NOT NULL,
	cantidad_base_disponible numeric(18, 6) NOT NULL,
	costo_unitario_base numeric(18, 6) DEFAULT 0 NOT NULL,
	estado varchar(30) DEFAULT 'activo'::character varying NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_lote_inventario_producto_cantidad CHECK (((cantidad_base_inicial > (0)::numeric) AND (cantidad_base_disponible >= (0)::numeric) AND (cantidad_base_disponible <= cantidad_base_inicial))),
	CONSTRAINT chk_lote_inventario_producto_codigo CHECK ((btrim((codigo_lote)::text) <> ''::text)),
	CONSTRAINT chk_lote_inventario_producto_costo CHECK ((costo_unitario_base >= (0)::numeric)),
	CONSTRAINT chk_lote_inventario_producto_estado CHECK (((estado)::text = ANY ((ARRAY['activo'::character varying, 'agotado'::character varying, 'vencido'::character varying, 'bloqueado'::character varying, 'anulado'::character varying])::text[]))),
	CONSTRAINT lote_inventario_producto_pkey PRIMARY KEY (id_lote_inventario_producto),
	CONSTRAINT uq_lote_inventario_producto_scope_codigo UNIQUE (id_empresa, id_producto, id_sucursal, codigo_lote),
	CONSTRAINT uq_lote_inventario_producto_scope_id UNIQUE (id_lote_inventario_producto, id_empresa, id_producto, id_sucursal),
	CONSTRAINT fk_lote_inventario_producto_presentacion FOREIGN KEY (id_producto_paquete_recepcion,id_empresa,id_producto) REFERENCES system_pos.producto_paquete(id_producto_paquete,id_empresa,id_producto) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_lote_inventario_producto_saldo_scope FOREIGN KEY (id_saldo_inventario_producto_base,id_empresa,id_producto,id_sucursal) REFERENCES system_pos.saldo_inventario_producto_sucursal_base(id_saldo_inventario_producto_base,id_empresa,id_producto,id_sucursal) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_lote_inventario_producto_fefo ON system_pos.lote_inventario_producto USING btree (id_empresa, id_producto, id_sucursal, fecha_vencimiento, id_lote_inventario_producto) WHERE (((estado)::text = 'activo'::text) AND (cantidad_base_disponible > (0)::numeric));


-- system_pos.metrica_producto_semanal definition

-- Drop table

-- DROP TABLE system_pos.metrica_producto_semanal;

CREATE TABLE system_pos.metrica_producto_semanal (
	id_metrica_producto_semanal bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_producto int8 NOT NULL,
	id_sucursal int8 NULL,
	semana_inicio date NOT NULL,
	semana_fin date NOT NULL,
	unidades_vendidas numeric(14, 2) DEFAULT 0 NOT NULL,
	ingresos numeric(14, 2) DEFAULT 0 NOT NULL,
	margen_estimado numeric(14, 2) DEFAULT 0 NOT NULL,
	stock_promedio numeric(14, 2) DEFAULT 0 NOT NULL,
	dias_sin_rotacion int4 DEFAULT 0 NOT NULL,
	clasificacion varchar(40) NULL,
	fecha_calculo timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_metrica_producto_rango CHECK ((semana_fin >= semana_inicio)),
	CONSTRAINT metrica_producto_semanal_pkey PRIMARY KEY (id_metrica_producto_semanal),
	CONSTRAINT uq_metrica_producto_semanal UNIQUE (id_empresa, id_producto, id_sucursal, semana_inicio, semana_fin),
	CONSTRAINT fk_metrica_producto_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_metrica_producto_producto FOREIGN KEY (id_producto) REFERENCES system_pos.producto(id_producto) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_metrica_producto_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX idx_metrica_producto_empresa_producto ON system_pos.metrica_producto_semanal USING btree (id_empresa, id_producto, semana_inicio DESC);


-- system_pos.movimiento_inventario_producto definition

-- Drop table

-- DROP TABLE system_pos.movimiento_inventario_producto;

CREATE TABLE system_pos.movimiento_inventario_producto (
	id_movimiento_inventario_producto int8 DEFAULT nextval('system_pos.seq_movimiento_inventario_producto'::regclass) NOT NULL,
	id_empresa int8 NOT NULL,
	id_producto int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	id_usuario int8 NULL,
	id_producto_paquete_presentacion int8 NULL,
	id_lote_inventario_producto int8 NULL,
	tipo_movimiento varchar(40) NOT NULL,
	cantidad_base_firmada numeric(18, 6) NOT NULL,
	unidades_por_item_usadas numeric(18, 6) NOT NULL,
	referencia_tipo varchar(60) NULL,
	referencia_id int8 NULL,
	motivo varchar(200) NULL,
	fecha_movimiento timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_movimiento_inventario_producto_cantidad CHECK ((cantidad_base_firmada <> (0)::numeric)),
	CONSTRAINT chk_movimiento_inventario_producto_factor CHECK ((unidades_por_item_usadas > (0)::numeric)),
	CONSTRAINT chk_movimiento_inventario_producto_tipo CHECK (((tipo_movimiento)::text = ANY ((ARRAY['entrada'::character varying, 'salida'::character varying, 'ajuste'::character varying, 'compra'::character varying, 'venta'::character varying, 'devolucion'::character varying, 'anulacion'::character varying, 'conversion'::character varying])::text[]))),
	CONSTRAINT movimiento_inventario_producto_pkey PRIMARY KEY (id_movimiento_inventario_producto),
	CONSTRAINT uq_movimiento_inventario_producto_scope_id UNIQUE (id_movimiento_inventario_producto, id_empresa, id_producto, id_sucursal),
	CONSTRAINT fk_movimiento_inventario_producto_lote_scope FOREIGN KEY (id_lote_inventario_producto,id_empresa,id_producto,id_sucursal) REFERENCES system_pos.lote_inventario_producto(id_lote_inventario_producto,id_empresa,id_producto,id_sucursal) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_movimiento_inventario_producto_presentacion FOREIGN KEY (id_producto_paquete_presentacion,id_empresa,id_producto) REFERENCES system_pos.producto_paquete(id_producto_paquete,id_empresa,id_producto) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_movimiento_inventario_producto_producto_empresa FOREIGN KEY (id_producto,id_empresa) REFERENCES system_pos.producto(id_producto,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_movimiento_inventario_producto_sucursal_empresa FOREIGN KEY (id_sucursal,id_empresa) REFERENCES system_pos.sucursal(id_sucursal,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_movimiento_inventario_producto_usuario_empresa FOREIGN KEY (id_usuario,id_empresa) REFERENCES system_pos.usuario(id_usuario,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_movimiento_inventario_producto_scope_fecha ON system_pos.movimiento_inventario_producto USING btree (id_empresa, id_producto, id_sucursal, fecha_movimiento DESC);

-- Table Triggers

create trigger trg_registrar_recepcion_compra_lote_producto after
insert
    or
update
    of tipo_movimiento,
    referencia_tipo,
    referencia_id,
    id_lote_inventario_producto,
    id_producto_paquete_presentacion,
    cantidad_base_firmada,
    id_empresa,
    id_sucursal,
    id_producto on
    system_pos.movimiento_inventario_producto for each row execute function system_pos.registrar_recepcion_compra_lote_producto();


-- system_pos.recepcion_compra_lote_producto definition

-- Drop table

-- DROP TABLE system_pos.recepcion_compra_lote_producto;

CREATE TABLE system_pos.recepcion_compra_lote_producto (
	id_recepcion_compra_lote_producto int8 DEFAULT nextval('system_pos.seq_recepcion_compra_lote_producto'::regclass) NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	id_producto int8 NOT NULL,
	id_detalle_compra int8 NOT NULL,
	id_producto_paquete_recepcion int8 NOT NULL,
	id_lote_inventario_producto int8 NOT NULL,
	id_movimiento_inventario_producto int8 NOT NULL,
	cantidad_base_recibida numeric(18, 6) NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_recepcion_compra_lote_producto_cantidad CHECK ((cantidad_base_recibida > (0)::numeric)),
	CONSTRAINT recepcion_compra_lote_producto_pkey PRIMARY KEY (id_recepcion_compra_lote_producto),
	CONSTRAINT uq_recepcion_compra_lote_producto_movimiento UNIQUE (id_movimiento_inventario_producto),
	CONSTRAINT fk_recepcion_compra_lote_producto_detalle_empresa FOREIGN KEY (id_detalle_compra,id_empresa) REFERENCES system_pos.detalle_compra(id_detalle_compra,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_recepcion_compra_lote_producto_lote_scope FOREIGN KEY (id_lote_inventario_producto,id_empresa,id_producto,id_sucursal) REFERENCES system_pos.lote_inventario_producto(id_lote_inventario_producto,id_empresa,id_producto,id_sucursal) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_recepcion_compra_lote_producto_movimiento_scope FOREIGN KEY (id_movimiento_inventario_producto,id_empresa,id_producto,id_sucursal) REFERENCES system_pos.movimiento_inventario_producto(id_movimiento_inventario_producto,id_empresa,id_producto,id_sucursal) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_recepcion_compra_lote_producto_presentacion FOREIGN KEY (id_producto_paquete_recepcion,id_empresa,id_producto) REFERENCES system_pos.producto_paquete(id_producto_paquete,id_empresa,id_producto) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_recepcion_compra_lote_producto_detalle ON system_pos.recepcion_compra_lote_producto USING btree (id_empresa, id_detalle_compra);
CREATE INDEX idx_recepcion_compra_lote_producto_lote ON system_pos.recepcion_compra_lote_producto USING btree (id_empresa, id_producto, id_sucursal, id_lote_inventario_producto);

-- Table Triggers

create trigger trg_validar_recepcion_compra_lote_producto before
insert
    or
update
    on
    system_pos.recepcion_compra_lote_producto for each row execute function system_pos.validar_recepcion_compra_lote_producto();


-- system_pos.asignacion_lote_movimiento_producto definition

-- Drop table

-- DROP TABLE system_pos.asignacion_lote_movimiento_producto;

CREATE TABLE system_pos.asignacion_lote_movimiento_producto (
	id_asignacion_lote_movimiento_producto int8 DEFAULT nextval('system_pos.seq_asignacion_lote_movimiento_producto'::regclass) NOT NULL,
	id_empresa int8 NOT NULL,
	id_producto int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	id_movimiento_inventario_producto int8 NOT NULL,
	id_lote_inventario_producto int8 NOT NULL,
	cantidad_base numeric(18, 6) NOT NULL,
	tipo_asignacion varchar(30) DEFAULT 'automatica'::character varying NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT asignacion_lote_movimiento_producto_pkey PRIMARY KEY (id_asignacion_lote_movimiento_producto),
	CONSTRAINT chk_asignacion_lote_movimiento_producto_cantidad CHECK ((cantidad_base > (0)::numeric)),
	CONSTRAINT chk_asignacion_lote_movimiento_producto_tipo CHECK (((tipo_asignacion)::text = ANY ((ARRAY['automatica'::character varying, 'manual'::character varying, 'restauracion'::character varying])::text[]))),
	CONSTRAINT fk_asignacion_lote_movimiento_producto_lote_scope FOREIGN KEY (id_lote_inventario_producto,id_empresa,id_producto,id_sucursal) REFERENCES system_pos.lote_inventario_producto(id_lote_inventario_producto,id_empresa,id_producto,id_sucursal) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_asignacion_lote_movimiento_producto_movimiento_scope FOREIGN KEY (id_movimiento_inventario_producto,id_empresa,id_producto,id_sucursal) REFERENCES system_pos.movimiento_inventario_producto(id_movimiento_inventario_producto,id_empresa,id_producto,id_sucursal) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_asignacion_lote_movimiento_producto_movimiento ON system_pos.asignacion_lote_movimiento_producto USING btree (id_movimiento_inventario_producto);


-- system_pos.detalle_devolucion_venta definition

-- Drop table

-- DROP TABLE system_pos.detalle_devolucion_venta;

CREATE TABLE system_pos.detalle_devolucion_venta (
	id_detalle_devolucion bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_devolucion_venta int8 NOT NULL,
	id_detalle_venta int8 NOT NULL,
	id_producto int8 NOT NULL,
	id_producto_paquete int8 NOT NULL,
	cantidad numeric(12, 2) NOT NULL,
	valor_unitario numeric(12, 2) NOT NULL,
	subtotal numeric(12, 2) NOT NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT detalle_devolucion_venta_cantidad_check CHECK ((cantidad > (0)::numeric)),
	CONSTRAINT detalle_devolucion_venta_pkey PRIMARY KEY (id_detalle_devolucion),
	CONSTRAINT detalle_devolucion_venta_subtotal_check CHECK ((subtotal >= (0)::numeric)),
	CONSTRAINT detalle_devolucion_venta_valor_unitario_check CHECK ((valor_unitario >= (0)::numeric)),
	CONSTRAINT fk_detalle_devolucion_devolucion FOREIGN KEY (id_devolucion_venta) REFERENCES system_pos.devolucion_venta(id_devolucion_venta) ON DELETE CASCADE,
	CONSTRAINT fk_detalle_devolucion_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa),
	CONSTRAINT fk_detalle_devolucion_producto FOREIGN KEY (id_producto) REFERENCES system_pos.producto(id_producto),
	CONSTRAINT fk_detalle_devolucion_sellable FOREIGN KEY (id_producto_paquete) REFERENCES system_pos.producto_paquete(id_producto_paquete),
	CONSTRAINT fk_detalle_devolucion_venta FOREIGN KEY (id_detalle_venta) REFERENCES system_pos.detalle_venta(id_detalle_venta)
);
CREATE INDEX idx_detalle_devolucion_sale_detail ON system_pos.detalle_devolucion_venta USING btree (id_detalle_venta);


-- system_pos.gasto definition

-- Drop table

-- DROP TABLE system_pos.gasto;

CREATE TABLE system_pos.gasto (
	id_gasto bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NULL,
	id_categoria_gasto int8 NOT NULL,
	id_usuario int8 NOT NULL,
	descripcion text NOT NULL,
	monto numeric(14, 2) NOT NULL,
	fecha_gasto timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	referencia varchar(120) NULL,
	estado varchar(30) DEFAULT 'registrado'::character varying NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	metodo_pago varchar(30) NULL,
	proveedor_id int8 NULL,
	proveedor_nombre varchar(150) NULL,
	iva_incluido bool DEFAULT false NOT NULL,
	iva_monto numeric(14, 2) DEFAULT 0 NOT NULL,
	adjuntos jsonb DEFAULT '[]'::jsonb NOT NULL,
	tercero_nombre text NULL,
	tercero_nit text NULL,
	id_compra int8 NULL,
	id_gasto_recurrente int8 NULL,
	fecha_programada date NULL,
	id_movimiento_inventario_producto int8 NULL,
	CONSTRAINT chk_gasto_estado CHECK (((estado)::text = ANY ((ARRAY['registrado'::character varying, 'anulado'::character varying])::text[]))),
	CONSTRAINT chk_gasto_iva_monto_contract CHECK ((iva_monto >= (0)::numeric)),
	CONSTRAINT chk_gasto_metodo_pago_contract CHECK (((metodo_pago IS NULL) OR ((metodo_pago)::text = ANY ((ARRAY['efectivo'::character varying, 'tarjeta'::character varying, 'transferencia'::character varying, 'credito'::character varying])::text[])))),
	CONSTRAINT chk_gasto_monto CHECK ((monto >= (0)::numeric)),
	CONSTRAINT chk_gasto_proveedor_tercero_excluyente CHECK (((proveedor_id IS NULL) OR ((tercero_nombre IS NULL) AND (tercero_nit IS NULL)))),
	CONSTRAINT chk_gasto_recurrente_periodo_consistente CHECK (((id_gasto_recurrente IS NULL) = (fecha_programada IS NULL))),
	CONSTRAINT gasto_pkey PRIMARY KEY (id_gasto),
	CONSTRAINT fk_gasto_categoria FOREIGN KEY (id_categoria_gasto) REFERENCES system_pos.categoria_gasto(id_categoria_gasto) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_gasto_categoria_empresa FOREIGN KEY (id_empresa,id_categoria_gasto) REFERENCES system_pos.categoria_gasto(id_empresa,id_categoria_gasto) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_gasto_compra FOREIGN KEY (id_compra) REFERENCES system_pos.compra(id_compra) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_gasto_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_gasto_gasto_recurrente FOREIGN KEY (id_gasto_recurrente) REFERENCES system_pos.gasto_recurrente(id_gasto_recurrente) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT fk_gasto_movimiento_inventario_producto FOREIGN KEY (id_movimiento_inventario_producto) REFERENCES system_pos.movimiento_inventario_producto(id_movimiento_inventario_producto) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_gasto_proveedor_contract FOREIGN KEY (proveedor_id) REFERENCES system_pos.proveedor(id_proveedor) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_gasto_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_gasto_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_gasto_compra ON system_pos.gasto USING btree (id_compra) WHERE (id_compra IS NOT NULL);
CREATE INDEX idx_gasto_empresa_categoria_fecha ON system_pos.gasto USING btree (id_empresa, id_categoria_gasto, fecha_gasto DESC);
CREATE INDEX idx_gasto_empresa_estado_fecha ON system_pos.gasto USING btree (id_empresa, estado, fecha_gasto DESC);
CREATE INDEX idx_gasto_empresa_fecha ON system_pos.gasto USING btree (id_empresa, fecha_gasto DESC);
CREATE INDEX idx_gasto_empresa_metodo_fecha ON system_pos.gasto USING btree (id_empresa, metodo_pago, fecha_gasto DESC) WHERE ((estado)::text = 'registrado'::text);
CREATE INDEX idx_gasto_empresa_tercero ON system_pos.gasto USING btree (id_empresa, tercero_nombre, tercero_nit) WHERE ((tercero_nombre IS NOT NULL) OR (tercero_nit IS NOT NULL));
CREATE INDEX idx_gasto_financial_range ON system_pos.gasto USING btree (id_empresa, fecha_gasto DESC) WHERE ((estado)::text = 'registrado'::text);
CREATE INDEX idx_gasto_id_gasto_recurrente ON system_pos.gasto USING btree (id_gasto_recurrente) WHERE (id_gasto_recurrente IS NOT NULL);
CREATE UNIQUE INDEX uq_gasto_empresa_compra ON system_pos.gasto USING btree (id_empresa, id_compra) WHERE (id_compra IS NOT NULL);
CREATE UNIQUE INDEX uq_gasto_empresa_movimiento_inventario ON system_pos.gasto USING btree (id_empresa, id_movimiento_inventario_producto) WHERE (id_movimiento_inventario_producto IS NOT NULL);
CREATE UNIQUE INDEX uq_gasto_recurrente_periodo ON system_pos.gasto USING btree (id_empresa, id_gasto_recurrente, fecha_programada) WHERE (id_gasto_recurrente IS NOT NULL);


-- system_pos.abono_venta definition

-- Drop table

-- DROP TABLE system_pos.abono_venta;

CREATE TABLE system_pos.abono_venta (
	id_abono_venta bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	id_venta int8 NOT NULL,
	id_cliente int8 NOT NULL,
	id_usuario int8 NOT NULL,
	id_metodo_pago int8 NOT NULL,
	id_sesion_caja int8 NULL,
	monto numeric(14, 2) NOT NULL,
	referencia varchar(120) NULL,
	observacion text NULL,
	fecha_abono timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	estado varchar(20) DEFAULT 'confirmado'::character varying NOT NULL,
	idempotency_key uuid NOT NULL,
	id_ingreso int8 NULL,
	id_movimiento_caja int8 NULL,
	fecha_anulacion timestamptz NULL,
	id_usuario_anulacion int8 NULL,
	motivo_anulacion text NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	id_abono_cliente_lote int8 NULL,
	CONSTRAINT abono_venta_pkey PRIMARY KEY (id_abono_venta),
	CONSTRAINT chk_abono_venta_anulacion CHECK (((((estado)::text = 'confirmado'::text) AND (fecha_anulacion IS NULL) AND (id_usuario_anulacion IS NULL) AND (motivo_anulacion IS NULL)) OR (((estado)::text = 'anulado'::text) AND (fecha_anulacion IS NOT NULL) AND (id_usuario_anulacion IS NOT NULL) AND (NULLIF(btrim(motivo_anulacion), ''::text) IS NOT NULL)))),
	CONSTRAINT chk_abono_venta_estado CHECK (((estado)::text = ANY ((ARRAY['confirmado'::character varying, 'anulado'::character varying])::text[]))),
	CONSTRAINT chk_abono_venta_monto CHECK ((monto > (0)::numeric)),
	CONSTRAINT uq_abono_venta_empresa_id UNIQUE (id_empresa, id_abono_venta),
	CONSTRAINT uq_abono_venta_empresa_idempotency UNIQUE (id_empresa, idempotency_key)
);
CREATE INDEX idx_abono_venta_estado_cuenta ON system_pos.abono_venta USING btree (id_empresa, id_cliente, fecha_abono DESC) WHERE ((estado)::text = 'confirmado'::text);
CREATE INDEX idx_abono_venta_lote ON system_pos.abono_venta USING btree (id_abono_cliente_lote) WHERE (id_abono_cliente_lote IS NOT NULL);
CREATE INDEX idx_abono_venta_sesion_caja ON system_pos.abono_venta USING btree (id_empresa, id_sesion_caja) WHERE (id_sesion_caja IS NOT NULL);
CREATE INDEX idx_abono_venta_venta_fecha ON system_pos.abono_venta USING btree (id_empresa, id_venta, fecha_abono DESC);
CREATE UNIQUE INDEX uq_abono_venta_ingreso ON system_pos.abono_venta USING btree (id_ingreso) WHERE (id_ingreso IS NOT NULL);
CREATE UNIQUE INDEX uq_abono_venta_movimiento_caja ON system_pos.abono_venta USING btree (id_movimiento_caja) WHERE (id_movimiento_caja IS NOT NULL);

-- Table Triggers

create trigger trg_abono_venta_saldo_neto before
insert
    on
    system_pos.abono_venta for each row execute function system_pos.validar_abono_contra_saldo_neto();
create trigger trg_recalcular_saldo_venta_desde_abonos after
insert
    or
update
    of estado on
    system_pos.abono_venta for each row execute function system_pos.recalcular_saldo_venta_desde_abonos();
create trigger trg_validar_y_proteger_abono_venta before
insert
    or
delete
    or
update
    on
    system_pos.abono_venta for each row execute function system_pos.validar_y_proteger_abono_venta();


-- system_pos.ingreso definition

-- Drop table

-- DROP TABLE system_pos.ingreso;

CREATE TABLE system_pos.ingreso (
	id_ingreso bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NULL,
	id_venta int8 NULL,
	id_usuario int8 NOT NULL,
	id_metodo_pago int8 NULL,
	descripcion text NOT NULL,
	monto numeric(14, 2) NOT NULL,
	fecha_ingreso timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	referencia varchar(120) NULL,
	origen varchar(40) DEFAULT 'venta_pos'::character varying NOT NULL,
	estado varchar(30) DEFAULT 'registrado'::character varying NOT NULL,
	fecha_creacion timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	actualizado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	id_abono_venta int8 NULL,
	CONSTRAINT chk_ingreso_abono_venta_origen CHECK (((((origen)::text = 'abono_venta'::text) AND (id_abono_venta IS NOT NULL) AND (id_venta IS NULL)) OR (((origen)::text <> 'abono_venta'::text) AND (id_abono_venta IS NULL)))) NOT VALID,
	CONSTRAINT chk_ingreso_estado CHECK (((estado)::text = ANY ((ARRAY['registrado'::character varying, 'anulado'::character varying])::text[]))),
	CONSTRAINT chk_ingreso_monto CHECK ((monto >= (0)::numeric)),
	CONSTRAINT chk_ingreso_origen CHECK (((origen)::text = ANY ((ARRAY['venta_pos'::character varying, 'manual'::character varying, 'ajuste'::character varying, 'abono_venta'::character varying])::text[]))) NOT VALID,
	CONSTRAINT ingreso_pkey PRIMARY KEY (id_ingreso),
	CONSTRAINT uq_ingreso_empresa_id UNIQUE (id_empresa, id_ingreso),
	CONSTRAINT uq_ingreso_venta UNIQUE (id_venta)
);
CREATE INDEX idx_ingreso_abono_venta ON system_pos.ingreso USING btree (id_empresa, id_abono_venta) WHERE (id_abono_venta IS NOT NULL);
CREATE INDEX idx_ingreso_empresa_fecha ON system_pos.ingreso USING btree (id_empresa, fecha_ingreso DESC);
CREATE INDEX idx_ingreso_empresa_sucursal_fecha ON system_pos.ingreso USING btree (id_empresa, id_sucursal, fecha_ingreso DESC);
CREATE INDEX idx_ingreso_estado_fecha ON system_pos.ingreso USING btree (estado, fecha_ingreso DESC);
CREATE INDEX idx_ingreso_financial_range ON system_pos.ingreso USING btree (id_empresa, fecha_ingreso DESC) WHERE ((estado)::text = 'registrado'::text);
CREATE UNIQUE INDEX uq_ingreso_abono_venta ON system_pos.ingreso USING btree (id_abono_venta) WHERE (id_abono_venta IS NOT NULL);


-- system_pos.movimiento_caja definition

-- Drop table

-- DROP TABLE system_pos.movimiento_caja;

CREATE TABLE system_pos.movimiento_caja (
	id_movimiento_caja bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sesion_caja int8 NOT NULL,
	id_usuario int8 NOT NULL,
	tipo_movimiento varchar(30) NOT NULL,
	origen varchar(40) DEFAULT 'manual'::character varying NOT NULL,
	referencia_tipo varchar(60) NULL,
	referencia_id int8 NULL,
	monto numeric(14, 2) NOT NULL,
	descripcion text NULL,
	fecha_movimiento timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	sentido varchar(10) DEFAULT 'entrada'::character varying NOT NULL,
	metodo_pago varchar(30) NULL,
	referencia varchar(100) NULL,
	venta_offline bool DEFAULT false NOT NULL,
	requiere_revision_caja bool DEFAULT false NOT NULL,
	id_abono_venta int8 NULL,
	id_pago_compra int8 NULL,
	afecta_caja bool DEFAULT true NOT NULL,
	CONSTRAINT chk_movimiento_caja_metodo_pago_contract CHECK (((metodo_pago IS NULL) OR ((metodo_pago)::text = ANY ((ARRAY['efectivo'::character varying, 'tarjeta'::character varying, 'transferencia'::character varying, 'credito'::character varying])::text[])))),
	CONSTRAINT chk_movimiento_caja_monto CHECK ((monto >= (0)::numeric)),
	CONSTRAINT chk_movimiento_caja_sentido CHECK (((sentido)::text = ANY ((ARRAY['entrada'::character varying, 'salida'::character varying])::text[]))),
	CONSTRAINT chk_movimiento_caja_tipo CHECK (((tipo_movimiento)::text = ANY ((ARRAY['ingreso'::character varying, 'egreso'::character varying, 'ajuste'::character varying, 'apertura'::character varying, 'cierre'::character varying, 'traslado'::character varying])::text[]))),
	CONSTRAINT movimiento_caja_pkey PRIMARY KEY (id_movimiento_caja),
	CONSTRAINT uq_movimiento_caja_empresa_id UNIQUE (id_empresa, id_movimiento_caja)
);
CREATE INDEX idx_movimiento_caja_abono_venta ON system_pos.movimiento_caja USING btree (id_empresa, id_abono_venta) WHERE (id_abono_venta IS NOT NULL);
CREATE INDEX idx_movimiento_caja_auditoria ON system_pos.movimiento_caja USING btree (id_empresa, id_usuario, fecha_movimiento DESC);
CREATE INDEX idx_movimiento_caja_empresa_fecha ON system_pos.movimiento_caja USING btree (id_empresa, fecha_movimiento DESC);
CREATE INDEX idx_movimiento_caja_offline_revision ON system_pos.movimiento_caja USING btree (id_empresa, requiere_revision_caja, fecha_movimiento DESC) WHERE (venta_offline = true);
CREATE INDEX idx_movimiento_caja_pago_compra ON system_pos.movimiento_caja USING btree (id_empresa, id_pago_compra) WHERE (id_pago_compra IS NOT NULL);
CREATE INDEX idx_movimiento_caja_sesion ON system_pos.movimiento_caja USING btree (id_sesion_caja, fecha_movimiento DESC);
CREATE INDEX idx_movimiento_caja_sesion_afecta ON system_pos.movimiento_caja USING btree (id_sesion_caja, afecta_caja);
CREATE INDEX idx_movimiento_caja_sesion_fecha ON system_pos.movimiento_caja USING btree (id_sesion_caja, fecha_movimiento DESC);
CREATE INDEX idx_movimiento_caja_tipo_sentido ON system_pos.movimiento_caja USING btree (tipo_movimiento, sentido);
CREATE UNIQUE INDEX uq_movimiento_caja_abono_venta ON system_pos.movimiento_caja USING btree (id_abono_venta) WHERE (id_abono_venta IS NOT NULL);
CREATE UNIQUE INDEX uq_movimiento_caja_pago_compra ON system_pos.movimiento_caja USING btree (id_pago_compra) WHERE (id_pago_compra IS NOT NULL);


-- system_pos.pago_compra definition

-- Drop table

-- DROP TABLE system_pos.pago_compra;

CREATE TABLE system_pos.pago_compra (
	id_pago_compra bigserial NOT NULL,
	id_empresa int8 NOT NULL,
	id_sucursal int8 NOT NULL,
	id_compra int8 NOT NULL,
	id_usuario int8 NOT NULL,
	id_metodo_pago int8 NOT NULL,
	id_sesion_caja int8 NULL,
	monto numeric(14, 2) NOT NULL,
	referencia varchar(120) NULL,
	observacion text NULL,
	fecha_pago timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	estado varchar(20) DEFAULT 'confirmado'::character varying NOT NULL,
	idempotency_key uuid NOT NULL,
	id_movimiento_caja int8 NULL,
	fecha_anulacion timestamptz NULL,
	id_usuario_anulacion int8 NULL,
	motivo_anulacion text NULL,
	creado_en timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_pago_compra_anulacion CHECK (((((estado)::text = 'confirmado'::text) AND (fecha_anulacion IS NULL) AND (id_usuario_anulacion IS NULL) AND (motivo_anulacion IS NULL)) OR (((estado)::text = 'anulado'::text) AND (fecha_anulacion IS NOT NULL) AND (id_usuario_anulacion IS NOT NULL) AND (NULLIF(btrim(motivo_anulacion), ''::text) IS NOT NULL)))),
	CONSTRAINT chk_pago_compra_estado CHECK (((estado)::text = ANY ((ARRAY['confirmado'::character varying, 'anulado'::character varying])::text[]))),
	CONSTRAINT chk_pago_compra_monto CHECK ((monto > (0)::numeric)),
	CONSTRAINT pago_compra_pkey PRIMARY KEY (id_pago_compra),
	CONSTRAINT uq_pago_compra_empresa_id UNIQUE (id_empresa, id_pago_compra),
	CONSTRAINT uq_pago_compra_empresa_idempotency UNIQUE (id_empresa, idempotency_key)
);
CREATE INDEX idx_pago_compra_compra_fecha ON system_pos.pago_compra USING btree (id_empresa, id_compra, fecha_pago DESC);
CREATE INDEX idx_pago_compra_sesion_caja ON system_pos.pago_compra USING btree (id_empresa, id_sesion_caja) WHERE (id_sesion_caja IS NOT NULL);
CREATE UNIQUE INDEX uq_pago_compra_movimiento_caja ON system_pos.pago_compra USING btree (id_movimiento_caja) WHERE (id_movimiento_caja IS NOT NULL);


-- system_pos.abono_venta foreign keys

ALTER TABLE system_pos.abono_venta ADD CONSTRAINT fk_abono_venta_cliente_empresa FOREIGN KEY (id_empresa,id_cliente) REFERENCES system_pos.cliente(id_empresa,id_cliente) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.abono_venta ADD CONSTRAINT fk_abono_venta_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.abono_venta ADD CONSTRAINT fk_abono_venta_ingreso_empresa FOREIGN KEY (id_empresa,id_ingreso) REFERENCES system_pos.ingreso(id_empresa,id_ingreso) ON DELETE RESTRICT ON UPDATE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE system_pos.abono_venta ADD CONSTRAINT fk_abono_venta_lote_empresa FOREIGN KEY (id_empresa,id_abono_cliente_lote) REFERENCES system_pos.abono_cliente_lote(id_empresa,id_abono_cliente_lote) ON DELETE RESTRICT ON UPDATE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE system_pos.abono_venta ADD CONSTRAINT fk_abono_venta_metodo_pago FOREIGN KEY (id_metodo_pago) REFERENCES system_pos.metodo_pago(id_metodo_pago) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.abono_venta ADD CONSTRAINT fk_abono_venta_movimiento_empresa FOREIGN KEY (id_empresa,id_movimiento_caja) REFERENCES system_pos.movimiento_caja(id_empresa,id_movimiento_caja) ON DELETE RESTRICT ON UPDATE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE system_pos.abono_venta ADD CONSTRAINT fk_abono_venta_sesion_empresa FOREIGN KEY (id_empresa,id_sesion_caja) REFERENCES system_pos.sesion_caja(id_empresa,id_sesion_caja) ON DELETE RESTRICT ON UPDATE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE system_pos.abono_venta ADD CONSTRAINT fk_abono_venta_sucursal_empresa FOREIGN KEY (id_sucursal,id_empresa) REFERENCES system_pos.sucursal(id_sucursal,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.abono_venta ADD CONSTRAINT fk_abono_venta_usuario_anulacion_empresa FOREIGN KEY (id_usuario_anulacion,id_empresa) REFERENCES system_pos.usuario(id_usuario,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.abono_venta ADD CONSTRAINT fk_abono_venta_usuario_empresa FOREIGN KEY (id_usuario,id_empresa) REFERENCES system_pos.usuario(id_usuario,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.abono_venta ADD CONSTRAINT fk_abono_venta_venta_empresa FOREIGN KEY (id_empresa,id_venta) REFERENCES system_pos.venta(id_empresa,id_venta) ON DELETE RESTRICT ON UPDATE CASCADE;


-- system_pos.ingreso foreign keys

ALTER TABLE system_pos.ingreso ADD CONSTRAINT fk_ingreso_abono_venta_empresa FOREIGN KEY (id_empresa,id_abono_venta) REFERENCES system_pos.abono_venta(id_empresa,id_abono_venta) ON DELETE RESTRICT ON UPDATE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE system_pos.ingreso ADD CONSTRAINT fk_ingreso_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.ingreso ADD CONSTRAINT fk_ingreso_metodo_pago FOREIGN KEY (id_metodo_pago) REFERENCES system_pos.metodo_pago(id_metodo_pago) ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE system_pos.ingreso ADD CONSTRAINT fk_ingreso_sucursal FOREIGN KEY (id_sucursal) REFERENCES system_pos.sucursal(id_sucursal) ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE system_pos.ingreso ADD CONSTRAINT fk_ingreso_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.ingreso ADD CONSTRAINT fk_ingreso_venta FOREIGN KEY (id_venta) REFERENCES system_pos.venta(id_venta) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.ingreso ADD CONSTRAINT fk_ingreso_venta_empresa FOREIGN KEY (id_empresa,id_venta) REFERENCES system_pos.venta(id_empresa,id_venta) ON DELETE RESTRICT ON UPDATE CASCADE;


-- system_pos.movimiento_caja foreign keys

ALTER TABLE system_pos.movimiento_caja ADD CONSTRAINT fk_movimiento_caja_abono_venta_empresa FOREIGN KEY (id_empresa,id_abono_venta) REFERENCES system_pos.abono_venta(id_empresa,id_abono_venta) ON DELETE RESTRICT ON UPDATE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE system_pos.movimiento_caja ADD CONSTRAINT fk_movimiento_caja_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.movimiento_caja ADD CONSTRAINT fk_movimiento_caja_pago_compra_empresa FOREIGN KEY (id_empresa,id_pago_compra) REFERENCES system_pos.pago_compra(id_empresa,id_pago_compra) ON DELETE RESTRICT ON UPDATE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE system_pos.movimiento_caja ADD CONSTRAINT fk_movimiento_caja_sesion FOREIGN KEY (id_sesion_caja) REFERENCES system_pos.sesion_caja(id_sesion_caja) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE system_pos.movimiento_caja ADD CONSTRAINT fk_movimiento_caja_usuario FOREIGN KEY (id_usuario) REFERENCES system_pos.usuario(id_usuario) ON DELETE RESTRICT ON UPDATE CASCADE;


-- system_pos.pago_compra foreign keys

ALTER TABLE system_pos.pago_compra ADD CONSTRAINT fk_pago_compra_compra FOREIGN KEY (id_compra) REFERENCES system_pos.compra(id_compra) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.pago_compra ADD CONSTRAINT fk_pago_compra_empresa FOREIGN KEY (id_empresa) REFERENCES system_pos.empresa(id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.pago_compra ADD CONSTRAINT fk_pago_compra_metodo_pago FOREIGN KEY (id_metodo_pago) REFERENCES system_pos.metodo_pago(id_metodo_pago) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.pago_compra ADD CONSTRAINT fk_pago_compra_movimiento_empresa FOREIGN KEY (id_empresa,id_movimiento_caja) REFERENCES system_pos.movimiento_caja(id_empresa,id_movimiento_caja) ON DELETE RESTRICT ON UPDATE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE system_pos.pago_compra ADD CONSTRAINT fk_pago_compra_sesion_empresa FOREIGN KEY (id_empresa,id_sesion_caja) REFERENCES system_pos.sesion_caja(id_empresa,id_sesion_caja) ON DELETE RESTRICT ON UPDATE CASCADE DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE system_pos.pago_compra ADD CONSTRAINT fk_pago_compra_sucursal FOREIGN KEY (id_sucursal,id_empresa) REFERENCES system_pos.sucursal(id_sucursal,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.pago_compra ADD CONSTRAINT fk_pago_compra_usuario FOREIGN KEY (id_usuario,id_empresa) REFERENCES system_pos.usuario(id_usuario,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE system_pos.pago_compra ADD CONSTRAINT fk_pago_compra_usuario_anulacion FOREIGN KEY (id_usuario_anulacion,id_empresa) REFERENCES system_pos.usuario(id_usuario,id_empresa) ON DELETE RESTRICT ON UPDATE CASCADE;